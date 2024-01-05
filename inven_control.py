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

 # Tkinter backend is used for rendering
matplotlib.use('TkAgg') 

# Global variable to store the current user's ID
current_user_id = None
graph_canvas = None

def main_app():
    # GUI window
    window = tk.Tk()
    window.title("Shop Inventory")
    window.geometry("900x700") # set fixed window size


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
        

    def log_change_to_db(item_name, original_quantity, new_quantity, current_user_id):
        db = mysql.connector.connect(
            host='localhost',
            database='shop_inventory',
            user='root',
            password='peter'
        )
        cursor = db.cursor()

        # Calculate the quantity change
        quantity_change = new_quantity - original_quantity

        # Insert the change record into changes_log
        insert_query = "INSERT INTO changes_log (item_name, original_quantity, new_quantity, quantity_change, emp_id) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(insert_query, (item_name, original_quantity, new_quantity, quantity_change, current_user_id))

        db.commit()
        db.close()


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

        log_change_to_db(item_name, current_quantity, new_quantity, current_user_id)

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

            # Update the changes dictionary with the quantity change
            if full_key in changes:
                changes[full_key] -= quantity_change
            else:
                changes[full_key] = -quantity_change

            # Update the quantity displayed in the GUI
            current_quantity = inventory[full_key]["Quantity"]
            new_quantity = current_quantity - quantity_change
            inventory[full_key]["Quantity"] = new_quantity
            quantity_label.config(text=f"Quantity: {new_quantity}")
            update_original_and_new_quantity(full_key, current_quantity, new_quantity)
            update_change_listbox(full_key, -quantity_change)

            # Log the change to the database
            log_change_to_db(item_name, current_quantity, new_quantity, current_user_id)
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
    toc_notebook.grid(row=0, column=1, columnspan=20, padx=10, pady=10, sticky='nsew')

    # Create frames for each tab
    daily_frame = ttk.Frame(toc_notebook)
    weekly_frame = ttk.Frame(toc_notebook)
    # monthly_frame = ttk.Frame(toc_notebook)
    toc_notebook.add(daily_frame, text='Daily Usage')
    toc_notebook.add(weekly_frame, text='Weekly Usage')
    # toc_notebook.add(monthly_frame, text='Monthly Usage')

    # Dropdown for month selection
    months = ['All Months'] + [datetime(2000, m, 1).strftime('%B') for m in range(1, 13)]  # List of months with 'All Months' as the first option
    month_var = tk.StringVar(window)
    month_combobox = ttk.Combobox(window, textvariable=month_var, values=months, state="readonly")
    month_combobox.current(0)  # Default to 'All Months'
    month_combobox.grid(row=1, column=1, padx=10, pady=5, sticky='w')

    toc_frames = {
        "Daily Usage": daily_frame,
        "Weekly Usage": weekly_frame,
        # "Monthly Usage": monthly_frame
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
        dates = [datetime.strptime(str(x[0]), "%Y-%m-%d") for x in data]
        quantities = [x[1] for x in data]

        fig, ax = plt.subplots(figsize=(10, 4))  # Adjust the size of plots

        # Check if dates list is empty
        if not dates:
            # empty list case here
            print("No data available for the selected item and time period.")
            return  # Skip drawing the graph

        ax.plot(dates, quantities, marker='o')  # Add markers for each data point
        plt.subplots_adjust(bottom=0.2)

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

    
    def item_selected(event):
        # Extract the item name from the selection
        selection = item_combobox.get()
        item_name = selection.split(" - ")[1] if " - " in selection else selection
        original_quantity = inventory.get(selection, {}).get("Quantity", "N/A")
        update_original_and_new_quantity(item_name, original_quantity, original_quantity)
        current_tab = toc_notebook.tab(toc_notebook.index("current"), "text").lower()
        draw_graph(item_name, current_tab)


    # Function to update the listbox with changes
    def update_change_listbox(item_key, original_quantity, quantity_change):
        # Calculate the new quantity
        new_quantity = original_quantity + quantity_change

        # Format the change text correctly
        change_text = f"{item_key}: {original_quantity} + {quantity_change} = {new_quantity}"

        # Insert the formatted change text into the listbox
        changes_listbox.insert(tk.END, change_text)

        # Split item_key to get just the item name for logging to the database
        item_name = item_key.split(" - ")[1]
        log_change_to_db(item_name, original_quantity, new_quantity, current_user_id)


    def update_original_and_new_quantity(item_name, original_quantity, new_quantity):
        original_label.config(text=f"Original Quantity: {original_quantity}")
        new_label.config(text=f"New Quantity: {new_quantity}")


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


    def scan_code():
        print("scan_code called")
        scanner_thread = threading.Thread(target=run_scanner)
        scanner_thread.start()


    def run_scanner():
        print("run_scanner started")
        try:
            # Initialize the camera
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("Unable to access the camera")
                return

            cap.set(3, 640)  # Set width
            cap.set(4, 480)  # Set height
            camera = True

            while camera:
                success, frame = cap.read()
                if not success:
                    print("Failed to grab frame")
                    break

                decoded_objects = decode(frame)
                if decoded_objects:
                    for code in decoded_objects:
                        random_id = code.data.decode('utf-8')
                        print("Scanned Code:", random_id)

                        item_data = get_item_data_from_db(random_id)
                        if item_data:
                            # Assuming item_data[0] is the item_name
                            item_name = item_data[0]
                            print(f"Item found: {item_name}")

                            # Use tkinter's after method to safely update GUI from another thread
                            window.after(0, lambda: item_combobox.set(f"{random_id} - {item_name}"))
                            window.after(0, lambda: update_original_and_new_quantity(item_name, item_data[2], item_data[2]))

                            # Break out of the loop after successful scan
                            camera = False
                        else:
                            print("Item not found in database")

                        # Sleep to prevent immediate re-scanning
                        time.sleep(2)

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
        
    def get_item_data_from_db(random_id):
        # Connect to the MySQL database
        db = mysql.connector.connect(
            host='localhost',
            user='root',
            password='peter',
            database='shop_inventory'
        )
        cursor = db.cursor()

        # Query to find an item by its random_id
        query = "SELECT * FROM shop_inventory_count WHERE random_id = %s"
        cursor.execute(query, (random_id,))

        # Fetch one record
        item_data = cursor.fetchone()

        # Close the database connection
        cursor.close()
        db.close()

        return item_data       

    # Fetch data from the MySQL database and populate the inventory dictionary
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="peter",
        database="shop_inventory"
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
    logo_label.grid(row=0, column=0, padx=10, pady=10, sticky='nw')  # Place the label at the top left corner

    # Modify the item_combobox to use the updated inventory keys
    item_combobox = ttk.Combobox(window, textvariable=search_var)
    item_combobox.set("Select Item - ID")

    # Label styling
    label_style = ttk.Style()
    label_style.configure("Custom.TLabel", font=("Arial", 12), )
    quantity_label = ttk.Label(window, text="Quantity: ", style="Custom.TLabel")
    original_label = ttk.Label(window, text="Original Quantity: N/A", style="Custom.TLabel")
    quantity_change_label = ttk.Label(window, text="Change Quantity:", style="Custom.TLabel")
    quantity_change_entry = ttk.Entry(window)
    new_label = ttk.Label(window, text="New Quantity: N/A", style="Custom.TLabel")
    
    # Button dimensions
    button_width = 18  # Adjust width as needed
    button_height = 1  # Adjust height as needed

    # Button styling with fixed dimensions
    add_button = tk.Button(window, text="\u2795 Add Quantity", command=add_quantity, font=("Calibri", 9), bg='blue', fg='white', width=button_width, height=button_height)
    remove_button = tk.Button(window, text="\u2796 Remove Quantity", command=remove_quantity, font=("Calibri", 9), bg='red', fg='white', width=button_width, height=button_height)
    save_button = tk.Button(window, text="Save Changes", command=save_changes, font=("Calibri", 9), bg="green", fg="white", width=button_width, height=button_height)
    reset_button = tk.Button(window, text="Reset", command=reset_quantity, font=("Calibri", 9), bg='orange', fg='black', width=button_width, height=button_height)

    # Bind the item selection event to the item_selected function
    item_combobox.bind("<<ComboboxSelected>>", item_selected)


    # Bind the month_combobox to update the graph when the selection changes
    month_combobox.bind("<<ComboboxSelected>>", update_graph_for_month)

    # Add a button for scanning
    scan_button = tk.Button(window, text="Search by Code Scan", command=scan_code)
    scan_button.grid(row=8, column=0, pady=5)  # Adjust grid position as needed


    # GUI components in the window using grid
    item_combobox.grid(row=1, column=0, padx=10, pady=5, sticky='w')
    quantity_label.grid(row=2, column=0, padx=10, pady=5, sticky='w')
    quantity_change_label.grid(row=3, column=0, padx=0, pady=5, sticky='w')
    quantity_change_entry.grid(row=3, column=0, padx=130, pady=5, sticky='w')
    add_button.grid(row=4, column=0, pady=5)
    remove_button.grid(row=5, column=0, pady=5, sticky='s')  
    original_label.grid(row=2, column=0, padx=0, pady=5, sticky='w')  
    new_label.grid(row=6, column=0, padx=0, pady=5, sticky='w')
    save_button.grid(row=7, column=0, columnspan=2, padx=10, pady=5, sticky='w')
    reset_button.grid(row=5, column=1, pady=5, sticky='w')  


    # Title label for the Listbox
    changes_title_label = tk.Label(window, text="Recent Changes", font=("Arial", 12, "bold"))
    changes_title_label.grid(row=6, column=1, padx=10, pady=(10, 0), sticky='w')  # Adjust row, column, padx, pady as needed


    # Listbox to display the changes
    changes_listbox = tk.Listbox(window, width= 40, borderwidth=0, highlightthickness=0,)
    changes_listbox.grid(row=7, column=1, rowspan=6, padx=10, pady=10, sticky='ns')

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
