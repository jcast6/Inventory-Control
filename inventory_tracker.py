"""
Shop Inventory Application
Author: jcast6
Created on: 12/29/23
Description: This application is designed to manage and track inventory for a shop. 
It features a graphical user interface built with Tkinter and uses MySQL for data storage.

This software provided is a work in progress, with continuos updates applied. Please be sure to check for new versions on
https://github.com/jcast6/Inventory-Control

"""

import tkinter as tk
import tkinter.messagebox
import mysql.connector
from tkinter import ttk
from PIL import Image, ImageTk

# GUI window
window = tk.Tk()
window.title("Shop Inventory")
window.geometry("700x600") # set fixed window size


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


def is_valid_quantity(input_str):
    try:
        value = float(input_str)
        return value >= 0
    except ValueError:
        return False
    
def log_change_to_db(item_name, original_quantity, new_quantity):
    db = mysql.connector.connect(
        host='localhost',
        database='shop_inventory',
        user='root',
        password='peter'
    )
    cursor = db.cursor()

    # Insert the change record into changes_log
    insert_query = "INSERT INTO changes_log (item_name, original_quantity, new_quantity) VALUES (%s, %s, %s)"
    cursor.execute(insert_query, (item_name, original_quantity, new_quantity))

    db.commit()
    db.close()
    

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

    log_change_to_db(item_name, current_quantity, new_quantity)

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
        log_change_to_db(item_name, current_quantity, new_quantity)
    else:
        tkinter.messagebox.showwarning("Invalid Item", "The specified item was not found in the inventory.")


# Reset function to clear the 'Change Quantity' entry
def reset_quantity():
  quantity_change_entry.delete(0, tk.END)



def update_original_and_new_quantity(item_name, original_quantity, new_quantity):
    original_label.config(text=f"Original Quantity: {original_quantity}")
    new_label.config(text=f"New Quantity: {new_quantity}")


def item_selected(event):
    # Extract the item name from the selection
    selection = item_combobox.get()
    item_name = selection.split(" - ")[1] if " - " in selection else selection
    original_quantity = inventory.get(selection, {}).get("Quantity", "N/A")
    update_original_and_new_quantity(item_name, original_quantity, original_quantity)


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
    log_change_to_db(item_name, original_quantity, new_quantity)



search_inventory = {}  # Dictionary for searching


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
logo_image = Image.open("inven_con.png")  
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
# Button styling
add_button = tk.Button(window, text="\u2795 Add Quantity", command=add_quantity, font=("Arial", 12), bg='blue', fg='white')
remove_button = tk.Button(window, text="\u2796 Remove Quantity", command=remove_quantity, font=("Arial", 12), bg='red', fg='white')
save_button = tk.Button(window, text="Save Changes", command=save_changes, font=("Arial", 12), bg="green", fg="white")
reset_button = tk.Button(window, text="Reset", command=reset_quantity, font=("Arial", 12),bg='orange', fg='black')


# Bind the item selection event to the item_selected function
item_combobox.bind("<<ComboboxSelected>>", item_selected)


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
