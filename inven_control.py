"""
Shop Inventory Application
Created by: jcast6
Created on: 12/29/23
Description: This application is designed to manage and track inventory for a shop. 
It features a graphical user interface built with Tkinter and uses MySQL for data storage.

The software provided is a work in progress, with continuos updates applied. Please be sure to check for new versions on
https://github.com/jcast6/Inventory-Control

"""

import threading
import tkinter as tk
import tkinter.messagebox
import mysql.connector
from tkinter import ttk
from PIL import Image, ImageTk
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import calendar
from datetime import datetime, timedelta
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import cv2
from pyzbar.pyzbar import decode
import time
import json

 # Tkinter backend is used for rendering
matplotlib.use('TkAgg') 

# Global variable to store the current user's ID
current_user_id = None
graph_canvas = None

# Global variables for images to prevent garbage collection
global_button_images = {}

def main_app():
    # GUI window
    window = tk.Tk()
    window.title("Shop Inventory")
    window.geometry("900x700") # set fixed window size
    window.configure(background = 'light grey')


    # Callback function to close the database connection and exit
    def on_closing():
        db.close()
        window.destroy()

    # Set the callback function to be executed when the window is closed
    window.protocol("WM_DELETE_WINDOW", on_closing)


    # Initialize the changes dictionary to track item quantity changes
    changes = {}
    # inventory dictionary to store inventory data from the database
    inventory = {}
    # Dictionary for searching
    search_inventory = {}
        

    def is_valid_quantity(input_str):
        try:
            value = float(input_str)
            return value >= 0
        except ValueError:
            return False
        

    def add_quantity():
        selection = item_combobox.get()
        item_name = selection.split(" - ")[1] if " - " in selection else selection

        # Check if item_name is in the format stored in the inventory dictionary
        if any(item_name in key for key in inventory):
            # Find the full key for item_name
            full_key = next(key for key in inventory if item_name in key)
            
            quantity_str = quantity_change_entry.get()

            if not is_valid_quantity(quantity_str):
                tkinter.messagebox.showwarning("Invalid Input", "Please enter a valid positive number for quantity.")
                return

            quantity_change = float(quantity_str)

            if quantity_change >= 100:  # Define your threshold for a 'large amount'
                if not confirm_large_change(quantity_change):
                    return

            # Update the changes dictionary with the quantity change
            if full_key in changes:
                changes[full_key] += quantity_change
            else:
                changes[full_key] = quantity_change

            # Retrieve the original quantity before updating the inventory
            current_quantity = inventory[full_key]["Quantity"]
            new_quantity = current_quantity + quantity_change

            # Update the quantity displayed in the GUI
            quantity_label.config(text=f"Quantity: {new_quantity}")

            # Update the listbox before updating the inventory dictionary
            update_change_listbox(full_key, current_quantity, quantity_change)

            # Now update the inventory dictionary with the new quantity
            inventory[full_key]["Quantity"] = new_quantity
        
            quantity_label.config(text=f"Quantity: {new_quantity}")
            update_original_and_new_quantity(full_key, current_quantity, new_quantity)
            # update_change_listbox(full_key, quantity_change)
        else:
            tkinter.messagebox.showwarning("Invalid Item", "The specified item was not found in the inventory.")

        log_change_to_db(item_name, current_quantity, new_quantity, current_user_id, random_id)

    def remove_quantity():
        selection = item_combobox.get()
        item_name = selection.split(" - ")[1] if " - " in selection else selection

        # Check if item_name is in the format stored in the inventory dictionary
        if any(item_name in key for key in inventory):
            # Find the full key for item_name
            full_key = next(key for key in inventory if item_name in key)

            quantity_str = quantity_change_entry.get()

            if not is_valid_quantity(quantity_str):
                tkinter.messagebox.showwarning("Invalid Input", "Please enter a valid positive number for quantity.")
                return

            quantity_change = float(quantity_str)

            if quantity_change >= 100:  # Define your threshold for a 'large amount'
                if not confirm_large_change(quantity_change):
                    return

            # Capture the original quantity before making any changes
            original_quantity = inventory[full_key]["Quantity"]

            # Calculate the new quantity after subtracting the change
            new_quantity = original_quantity - quantity_change

            # Prevent new quantity from becoming negative
            if new_quantity < 0:
                tkinter.messagebox.showerror("Invalid Quantity", "Removal amount exceeds the current quantity.")
                return

            # Update the changes dictionary with the quantity change
            if full_key in changes:
                changes[full_key] -= quantity_change
            else:
                changes[full_key] = -quantity_change

            # Update the inventory with the new quantity
            inventory[full_key]["Quantity"] = new_quantity

            # Update the GUI to reflect the new quantity
            quantity_label.config(text=f"Quantity: {new_quantity}")
            update_original_and_new_quantity(full_key, original_quantity, new_quantity)
            
            # Log the change to the database
            log_change_to_db(item_name, original_quantity, new_quantity, current_user_id, random_id)

            # Update the recent changes listbox. Pass the original quantity (unchanged) and the negative quantity change
            update_change_listbox(full_key, original_quantity, -quantity_change)
        else:
            tkinter.messagebox.showwarning("Invalid Item", "The specified item was not found in the inventory.")


    # Reset function to clear the 'Change Quantity' entry
    def reset_quantity():
        quantity_change_entry.delete(0, tk.END)

    def update_dropdown(*args):
        typed = search_var.get().lower()
        if typed:
            # Filter and update the dropdown list to show only matching items
            data = [f"{random_id} - {item}" for item, (random_id, _) in search_inventory.items() if typed in item.lower() or typed in random_id]
        else:
            # If no input, show all items
            data = list(inventory.keys())
        item_combobox['values'] = data

    search_var = tk.StringVar(window)
    search_var.trace('w', update_dropdown)


    # Create a ttk Notebook for the Table of Contents
    toc_notebook = ttk.Notebook(window)
    toc_notebook.grid(row = 0, column = 1, columnspan = 20, padx = 10, pady = 10, sticky = 'nsew')

    # Create frames for each tab
    daily_frame = ttk.Frame(toc_notebook)
    # weekly_frame = ttk.Frame(toc_notebook)
    # monthly_frame = ttk.Frame(toc_notebook)
    toc_notebook.add(daily_frame, text = 'Daily Usage')
    # toc_notebook.add(weekly_frame, text = 'Weekly Usage')
    # toc_notebook.add(monthly_frame, text='Monthly Usage')

    # Dropdown for month selection
    months = ['All Months'] + [datetime(2000, m, 1).strftime('%B') for m in range(1, 13)]  # List of months with 'All Months' as the first option
    month_var = tk.StringVar(window)
    month_combobox = ttk.Combobox(window, textvariable=month_var, values=months, state="readonly")
    month_combobox.current(0)  # Default to 'All Months'
    month_combobox.grid(row = 1, column = 1, padx = 10, pady = 5, sticky = 'w')

    toc_frames = {
        "Daily Usage": daily_frame,
    }

    
    def draw_graph(item_name, time_period, selected_month = None):
        global graph_canvas
        
        # If no item is selected, do nothing
        if not item_name:
            return

        # Clear previous graph if it exists
        if graph_canvas:
            graph_canvas.get_tk_widget().destroy()

        # Connect to the database
        db = mysql.connector.connect(
            host='localhost',
            user='root',
            password='peter',
            database='shop_inventory'
        )
        cursor = db.cursor()

        # SQL query to filter data based on the selected month
        month_condition = ""
        if selected_month and selected_month != 'All Months':
            month_number = datetime.strptime(selected_month, '%B').month
            month_condition = f" AND MONTH(change_date) = {month_number}"

        # base query with GROUP BY clause
        base_query = """
            SELECT DATE(change_date) as date, SUM(quantity_change) as total_change 
            FROM changes_log 
            WHERE item_name = %s
            """

        # Append month condition if necessary
        if selected_month and selected_month != 'All Months':
            month_number = datetime.strptime(selected_month, '%B').month
            base_query += f" AND MONTH(change_date) = {month_number}"

        # Define group and order clauses based on the time period
        if time_period == "Daily Usage":
            base_query += " GROUP BY DATE(change_date) ORDER BY DATE(change_date)"
        else:  # Weekly Usage
            base_query += " GROUP BY YEARWEEK(change_date) ORDER BY YEARWEEK(change_date)"

        # Execute the query
        cursor.execute(base_query, (item_name,))

        # Fetch the data
        data = cursor.fetchall()
        
        # Process the data to create a list of dates, but only include valid date strings
        dates = []
        for x in data:
            if x[0] is not None:
                try:
                    date = datetime.strptime(str(x[0]), "%Y-%m-%d")
                    dates.append(date)
                except ValueError:
                    # If the date string is in the wrong format, skip it
                    continue

        quantities = [x[1] for x in data if x[0] is not None]

        fig, ax = plt.subplots(figsize=(8, 4))  # Adjust the size of plots

        # Check if dates list is empty
        if not dates:
            # empty list case here
            print("No data available for the selected item and time period.")
            return  # Skip drawing the graph

        ax.plot(dates, quantities, marker='o')  # Add markers for each data point
        plt.subplots_adjust(bottom=0.2)

        # if tab selected is Daily usage
        if time_period == "Daily Usage":
            first_date = dates[0].replace(day=1)  # First day of the month
            last_day = calendar.monthrange(dates[0].year, dates[0].month)[1]  # Get the last day of the month
            last_date = dates[0].replace(day=last_day)  # Last day of the month
            dates_range = mdates.drange(first_date, last_date + timedelta(days=1), timedelta(days=1))
            ax.set_xticks(dates_range)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=90, fontsize=6)
        elif time_period == "Weekly Usage":
            start_dates = [datetime.strptime(f'{date}-1', "%Y%W-%w") for date in dates]
            # Add one more week
            last_week = start_dates[-1] + timedelta(weeks=1)
            start_dates.append(last_week)
            ax.set_xticks(range(len(start_dates)))  # Set x-ticks to be the start dates of weeks
            ax.set_xticklabels([date.strftime('%Y-%W') for date in start_dates], rotation=45)  # Year-Week format


        # Check if the data list is empty or has only one data point
        if not data or len(data) == 1:
            # Handle the empty or single data point case
            if not data:
                print("No data available for the selected item and time period.")
                # You might want to clear the previous plot or display a message on the plot
            else:
                # If there's only one point, plot it with additional settings
                single_date = datetime.strptime(str(data[0][0]), "%Y-%m-%d")
                single_quantity = data[0][1]
                ax.plot(single_date, single_quantity, 'o')  # Plot the single point

                # Set a reasonable range around the single date for x-axis
                start_date = single_date - timedelta(days=10)
                end_date = single_date + timedelta(days=15)
                ax.set_xlim(start_date, end_date)

                # Formatting the date on the x-axis
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))  # Show every 5 days
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                plt.xticks(rotation=90, fontsize=6)

        # Embedding the figure in the Tkinter window
        graph_canvas = FigureCanvasTkAgg(fig, master=toc_frames[time_period])
        graph_canvas.draw()
        graph_widget = graph_canvas.get_tk_widget()
        graph_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Close the database connection
        cursor.close()
        db.close()


    def on_tab_selected(event):
        selected_tab = event.widget.tab(event.widget.index("current"), "text")
        selected_item = item_combobox.get().split(" - ")[1] if " - " in item_combobox.get() else None
        if selected_item:
            if selected_tab in ["Daily Usage", "Weekly Usage"]:  # Remove "Monthly Usage" from the condition
                draw_graph(selected_item, selected_tab)


    # Function to update the graph when a new month is selected
    def update_graph_for_month(event):
        selected_month = month_var.get()
        selected_item = item_combobox.get().split(" - ")[1] if " - " in item_combobox.get() else None
        selected_tab = toc_notebook.tab(toc_notebook.index("current"), "text")
        if selected_item:
            draw_graph(selected_item, selected_tab, selected_month)


    # Function to update the listbox with changes
    def update_change_listbox(item_key, original_quantity, quantity_change):
        # Calculate the new quantity
        new_quantity = original_quantity + quantity_change if quantity_change >= 0 else original_quantity - abs(quantity_change)

        # Determine the operation symbol and format the change appropriately
        operation = "+" if quantity_change >= 0 else "-"
        adjusted_quantity_change = abs(quantity_change)

        # Format the change text correctly for display in the listbox
        change_text = f"{item_key}: {original_quantity} {operation} {adjusted_quantity_change} = {new_quantity}"

        # Insert the formatted change text into the listbox
        changes_listbox.insert(tk.END, change_text)

        # Split item_key to get just the item name for logging to the database
        item_name = item_key.split(" ")[1]
        log_change_to_db(item_name, original_quantity, new_quantity, current_user_id, random_id)


    def update_original_and_new_quantity(item_name, original_quantity, new_quantity):
        original_label.config(text = f"Original Quantity: {original_quantity}")
        new_label.config(text = f"New Quantity: {new_quantity}")


    def item_selected(event):
        # Extract the item name from the selection
        selection = item_combobox.get()
        item_name = selection.split(" - ")[1] if " - " in selection else selection
        original_quantity = inventory.get(selection, {}).get("Quantity", "N/A")
        update_original_and_new_quantity(item_name, original_quantity, original_quantity)
        current_tab = toc_notebook.tab(toc_notebook.index("current"), "text").lower()
        draw_graph(item_name, current_tab)


    def item_selected(event):
        selection = item_combobox.get()
        item_name = selection.split(" - ")[1] if " - " in selection else selection
        original_quantity = inventory.get(selection, {}).get("Quantity", "N/A")
        update_original_and_new_quantity(item_name, original_quantity, original_quantity)
        current_tab = toc_notebook.tab(toc_notebook.index("current"), "text")
        if item_name:
            draw_graph(item_name, current_tab)
    

    def confirm_large_change(quantity_change):
        return tkinter.messagebox.askyesno("Confirm Large Change", f"Are you sure you want to change the quantity by {quantity_change}?")


    def save_changes():
        # Display a confirmation dialog
        confirmation = tkinter.messagebox.askyesno("Confirm Changes", "Are you sure you want to save the changes?")

        if confirmation:
            # Connect to the MySQL database
            db = mysql.connector.connect(
                host='localhost',
                database='shop_inventory',
                user='root',
                password='peter'
            )
            cursor = db.cursor()

            # Apply the changes to the database
            for key, quantity_change in changes.items():
                item_name = key.split(" - ")[1]  # Extract the actual ItemName
                update_query = f"UPDATE shop_inventory_count SET Quantity = Quantity + {quantity_change} WHERE ItemName = '{item_name}'"
                cursor.execute(update_query)

            # Commit the changes and close the database connection
            db.commit()
            db.close()

            # Close the GUI window
            window.destroy()


    def get_item_data_from_db(random_id):
        db = mysql.connector.connect(
            host = 'localhost',
            user = 'root',
            password = 'peter',
            database = 'shop_inventory'
        )
        cursor = db.cursor()

        # Query to find an item by its random_id
        query = "SELECT category, ItemName, quantity, random_id FROM shop_inventory_count WHERE random_id = %s"
        print("Executing query:", query)  # Debugging line
        print("With random_id:", random_id)  # Debugging line

        try:
            cursor.execute(query, (random_id,))
            item_data = cursor.fetchone()
            print("Query result:", item_data)  # Debugging line
        except Exception as e:
            print("An error occurred while executing the query:", e)
            item_data = None

        cursor.close()
        db.close()

        return item_data

    def scan_code():
        print("scan_code called")
        scanner_thread = threading.Thread(target = run_scanner)
        scanner_thread.start()

    def run_scanner():
        print("run_scanner started")
        try:
            # start camera
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("Unable to access the camera")
                return

            cap.set(3, 640)  # Set width
            cap.set(4, 480)  # Set height
            camera = True    # camera is on

            while camera:
                success, frame = cap.read()
                if not success:
                    print("Failed to grab frame") # camera did not open
                    break
                
                # scan code in front of camera
                decoded_objects = decode(frame)
                if decoded_objects:
                    for code in decoded_objects:
                        qr_data = code.data.decode('utf-8')
                        print("Scanned Code:", qr_data)

                        try:
                            qr_data_json = json.loads(qr_data)
                            random_id = qr_data_json.get("random_id")
                            if random_id:
                                item_data = get_item_data_from_db(random_id)
                                if item_data:
                                    category, ItemName, quantity, _ = item_data
                                    print(f"Item found: {ItemName}, Category: {category}, Quantity: {quantity}")
                                    ################ Update GUI and handle the data as here ######################
                                    # 
                                    #
                                    #
                                    #
                                    camera = False
                                else:
                                    print("Item not found in database")
                            else:
                                print("Random ID not found in QR data")
                        except json.JSONDecodeError:
                            print("Invalid QR code format")

                        # Sleep to prevent immediate re-scanning
                        time.sleep(5)

                cv2.imshow("Scanner Window", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except Exception as e:
            print("An error occurred in run_scanner:", e)
        finally:
            if 'cap' in locals() and cap.isOpened():
                cap.release()
            cv2.destroyAllWindows()
            print("Scanner stopped")

          
    def log_change_to_db(item_name, original_quantity, new_quantity, current_user_id, random_id):
        db = mysql.connector.connect(
            host='localhost',
            database='shop_inventory',
            user='root',
            password='peter'
        )
        cursor = db.cursor()

        # Calculate the quantity change
        quantity_change = new_quantity - original_quantity

        # Get the current timestamp
        change_time = datetime.now()
        change_date = change_time.date()  # Extracts just the date part of the datetime

        # Insert the change record into changes_log
        insert_query = "INSERT INTO changes_log(item_name, original_quantity, new_quantity, quantity_change, change_date, change_time, emp_id, random_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(insert_query, 
                    (item_name, original_quantity, new_quantity, quantity_change, change_date, change_time, current_user_id, random_id))

        db.commit()
        db.close()


    # Fetch data from the MySQL database and populate the inventory dictionary
    db = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "peter",
        database = "shop_inventory"
    )
    cursor = db.cursor()
    # Modify the SQL query to include random_id
    cursor.execute("SELECT ItemName, random_id, Quantity FROM shop_inventory_count")
    for (item_name, random_id, quantity) in cursor:
        inventory_key = f"{random_id} - {item_name}"
        inventory[inventory_key] = {"Quantity": quantity}
        search_inventory[item_name] = (random_id, quantity)  # Store for searching


    # Load and display the company logo image
    logo_image = Image.open("github_projects/logo-png.png")  
    logo_photo = ImageTk.PhotoImage(logo_image)
    logo_label = tk.Label(window, image=logo_photo)
    logo_label.grid(row = 0, column = 0, padx = 10, pady = 10, sticky = 'nw')  # Place the label at the top left corner

    # Modify the item_combobox to use the updated inventory keys
    item_combobox = ttk.Combobox(window, textvariable=search_var)
    item_combobox.set("Item Name Here - ID")

    # Label styling
    label_style = ttk.Style()
    label_style.configure("Custom.TLabel", font=("Arial", 12), )
    quantity_label = ttk.Label(window, text="Quantity: ", style="Custom.TLabel", background= 'light grey')
    original_label = ttk.Label(window, text="Original Quantity: N/A", style="Custom.TLabel", background= 'light grey')
    quantity_change_label = ttk.Label(window, text="Change Quantity:", style="Custom.TLabel", background= 'light grey')
    quantity_change_entry = ttk.Entry(window)
    new_label = ttk.Label(window, text="New Quantity: N/A", style="Custom.TLabel",  background= 'light grey')
    
    # Button dimensions
    button_width = 18  # Adjust width as needed
    button_height = 0.6  # Adjust height as needed

    # Default button border thickness
    original_thickness = 1  # Adjust this value as needed
    original_color = 'systemButtonFace'  # Default system color for buttons


    # Functions for button hover effect using a border frame
    def on_enter(e, frame):
        frame.config(highlightbackground='cyan', highlightthickness=1)

    def on_leave(e, frame):
        frame.config(highlightbackground='black', highlightthickness=1)


    # Create frames as borders for each button
    add_button_frame = tk.Frame(window, highlightbackground = 'black', highlightthickness = 1)
    remove_button_frame = tk.Frame(window, highlightbackground = 'black', highlightthickness = 1)
    save_button_frame = tk.Frame(window, highlightbackground = 'black', highlightthickness = 1)
    reset_button_frame = tk.Frame(window, highlightbackground = 'black', highlightthickness = 1)
    scan_button_frame = tk.Frame(window, highlightbackground = 'black', highlightthickness = 1)


    # Load and resize the background image for the 'Add Quantity' button
    add_button_image = Image.open("github_projects/button_colors/addition_background.png")
    resized_add_button_image = add_button_image.resize((110, 30))  # Resize the image (width, height)
    add_button_photo = ImageTk.PhotoImage(resized_add_button_image)
    global_button_images['add_button'] = add_button_photo  # Keep a reference

    # Load and resize images for other buttons (replace with actual paths)
    remove_button_image = Image.open("github_projects/button_colors/subtraction_background.png")
    save_button_image = Image.open("github_projects/button_colors/green_button.png")
    reset_button_image = Image.open("github_projects/button_colors/yellow_button.png")
    scan_button_image = Image.open("github_projects/button_colors/scanner_button_im.png")
    resized_remove_button_image = remove_button_image.resize((111, 31))
    resized_save_button_image = save_button_image.resize((110, 30))
    resized_reset_button_image = reset_button_image.resize((110, 30))
    resized_scan_button_image = scan_button_image.resize((110, 30))
    remove_button_photo = ImageTk.PhotoImage(resized_remove_button_image)
    save_button_photo = ImageTk.PhotoImage(resized_save_button_image)
    reset_button_photo = ImageTk.PhotoImage(resized_reset_button_image)
    scan_button_photo = ImageTk.PhotoImage(resized_scan_button_image)
    global_button_images['remove_button'] = remove_button_photo
    global_button_images['save_button'] = save_button_photo
    global_button_images['reset_button'] = reset_button_photo
    global_button_images['scan_button'] = scan_button_photo  # Keep a reference

    """
    # Button styling with images
    add_button = tk.Button(window, text="\u2795 Add Quantity", command=add_quantity, font=("Calibri", 9), image=add_button_photo, compound="center")
    remove_button = tk.Button(window, text="\u2796 Remove Quantity", command=remove_quantity, font=("Calibri", 9), image=remove_button_photo, compound="center")
    save_button = tk.Button(window, text="Save Changes", command=save_changes, font=("Calibri", 9), image=save_button_photo, compound="center")
    reset_button = tk.Button(window, text="Reset", command=reset_quantity, font=("Calibri", 9), image=reset_button_photo, compound="center")
    
    # Keep a reference to the images
    add_button.image = add_button_photo
    remove_button.image = remove_button_photo
    save_button.image = save_button_photo
    reset_button.image = reset_button_photo
    """


    # Create and place buttons inside the frames
    add_button = tk.Button(add_button_frame, text = "\u2795 Add Quantity", command = add_quantity, font = ("Calibri", 9), image = add_button_photo, compound = "center")
    remove_button = tk.Button(remove_button_frame, text = "\u2796 Remove Quantity", command = remove_quantity, font = ("Calibri", 9), image = remove_button_photo, compound = "center")
    save_button = tk.Button(save_button_frame, text = "Save Changes", command = save_changes, font = ("Calibri", 9), image = save_button_photo, compound = "center")
    reset_button = tk.Button(reset_button_frame, text = "Reset", command = reset_quantity, font = ("Calibri", 9), image = reset_button_photo, compound = "center")
    scan_button = tk.Button(scan_button_frame, text = " Search by code scan", command = scan_code, font = ("Calibri", 9), compound = "center")


    # Bind the item selection event to the item_selected function
    item_combobox.bind("<<ComboboxSelected>>", item_selected)


    # Bind the month_combobox to update the graph when the selection changes
    month_combobox.bind("<<ComboboxSelected>>", update_graph_for_month)


    # GUI components in the window using grid
    item_combobox.grid(row = 1, column = 0, padx = 10, pady = 5, sticky = 'w')
    quantity_label.grid(row = 2, column = 0, padx = 10, pady = 5, sticky = 'w')
    quantity_change_label.grid(row = 3, column = 0, padx = 10, pady = 5, sticky = 'w')
    quantity_change_entry.grid(row = 3, column = 0, padx = 140, pady = 5, sticky = 'w')
    add_button.grid(row = 4, column = 0, pady = 5)
    remove_button.grid(row = 5, column = 0, pady = 5, sticky = 's')  
    original_label.grid(row = 2, column = 0, padx = 10, pady = 5, sticky = 'w')  
    new_label.grid(row = 6, column = 0, padx = 10, pady = 5, sticky = 'w')
    save_button.grid(row = 7, column = 0, columnspan = 2, padx = 10, pady = 5, sticky = 'w')
    reset_button.grid(row = 5, column = 1, pady = 5, sticky = 'w')
    # Add a button for scanning
    # scan_button = tk.Button(window, text="Search by Code Scan", command=scan_code)
    scan_button.grid(row = 2, column = 3, padx=50, pady = 5)  # Adjust grid position as needed


    # Title label for the Listbox
    changes_title_label = tk.Label(window, text="Recent Changes", font=("Arial", 12, "bold"),  background= 'light grey')
    changes_title_label.grid(row = 6, column = 1, padx = 10, pady = (10, 0), sticky = 'w')  # Adjust row, column, padx, pady as needed


    # Listbox to display the changes
    changes_listbox = tk.Listbox(window, width = 40, borderwidth = 0, highlightthickness = 0,)
    changes_listbox.grid(row = 7, column = 1, rowspan = 6, padx = 10, pady = 10, sticky = 'ns')



    # Pack buttons into their frames
    add_button.pack()
    remove_button.pack()
    save_button.pack()
    reset_button.pack()
    scan_button.pack()

    # Grid the frames in the main window
    add_button_frame.grid(row = 4, column = 0, pady = 5)
    remove_button_frame.grid(row = 5, column = 0, pady = 5, sticky = 's')
    save_button_frame.grid(row = 7, column = 0, columnspan = 2, padx = 10, pady = 5, sticky = 'w')
    reset_button_frame.grid(row = 5, column = 1, pady = 5, padx = 10, sticky = 'w')
    scan_button_frame.grid(row = 1, column = 0, padx = (50, 0), pady = 5)  # Adjust grid position as needed



    # Bind the hover events for each frame
    for frame in [add_button_frame, remove_button_frame, save_button_frame, reset_button_frame]:
        frame.bind("<Enter>", lambda e, f=frame: on_enter(e, f))
        frame.bind("<Leave>", lambda e, f=frame: on_leave(e, f))


    # Start the GUI application
    window.mainloop()
    


# Tkinter window for the login page
login_window = tk.Tk()
login_window.title("Employee Login")
login_window.geometry("250x250")

#### Login and validation checking. ####
def validate_login():
    global current_user_id
    emp_id = emp_id_entry.get()
    last_name = last_name_entry.get()
    
    # Connect to the MySQL database
    db = mysql.connector.connect(
        host='localhost',
        user='root',
        password='peter',  # Replace with your MySQL password
        database='shop_inventory'
    )
    cursor = db.cursor()
    # Query to check if employee ID and last name exist in the database
    query = "SELECT * FROM emp_login WHERE id = %s AND last_name = %s"
    cursor.execute(query, (emp_id, last_name))
    result = cursor.fetchone()

    # Close the database connection
    cursor.close()
    db.close()

    if result:
        # keep the user_id saved
        current_user_id = emp_id
        # If the employee ID and last name are valid, close the login window and open the main application window
        login_window.destroy()
        open_main_window()
    else:
        # Show an error message if the login is invalid
        tkinter.messagebox.showerror("Login Failed", "Invalid Employee ID or Last Name")

# Create and place the widgets
tk.Label(login_window, text="Employee ID").pack()
emp_id_entry = tk.Entry(login_window)
emp_id_entry.pack()
tk.Label(login_window, text="Last Name").pack()
last_name_entry = tk.Entry(login_window)
last_name_entry.pack()
login_button = tk.Button(login_window, text="Login", command=validate_login)
login_button.pack()


def open_main_window():
    main_app()

# Start the Tkinter event loop

login_window.mainloop()
