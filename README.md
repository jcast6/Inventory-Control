# Inventory-Control
This Shop Inventory Management System is a GUI application built using Python and Tkinter, designed to facilitate inventory tracking, updating, and reporting in a warehouse shop environment. It integrates with a MySQL database for data storage and retrieval.

# Simple Login Window
Purpose: Secure access to the inventory management system. Employees enter their ID and last name to log in. The system verifies credentials from the MySQL database.
![image](https://github.com/jcast6/Inventory-Control/assets/89822103/ab52eb81-06a9-4b1f-a78e-b7210ad0f165)

# Main inventory page
Layout: Features a dropdown to select items, buttons for modifying item quantities, and visualizing inventory changes. Displays the current inventory, allows for the selection of items, and visualizes inventory changes over time.
![image](https://github.com/jcast6/Inventory-Control/assets/89822103/e42d781b-ea72-4779-9263-b22f3e61934b)

# User selects an item
Implementation: A dropdown menu (ComboBox) populated with inventory items. Users select an item to view or modify its details, including current quantity.
![image](https://github.com/jcast6/Inventory-Control/assets/89822103/69407330-c988-45ad-9af3-97b3cac760a2)

# User Adds or Removes a number pieces of selected item. 
![image](https://github.com/jcast6/Inventory-Control/assets/89822103/4bec69be-9ec4-4e71-9571-5614be4abc35)
Add Quantity: Increase the item quantity in the inventory.
Remove Quantity: Decrease the item quantity.
Threshold Confirmation: For large quantity changes, a confirmation prompt appears.
### User adds number of items with changes logged.
![image](https://github.com/jcast6/Inventory-Control/assets/89822103/1105d136-1ac7-49fb-988b-5a4204035d6f)
### User subtracts number of items with changes logged.
![image](https://github.com/jcast6/Inventory-Control/assets/89822103/f97e4042-4085-423d-aff0-1cb4d01df7ce)


# Select months to track inventory daily usage and changes.
Select Months to Track Inventory Daily Usage and Changes
Time Frame Selection: Dropdown to select a month for viewing inventory usage and changes.
Graph Representation: Plots inventory changes over the selected time frame on a graph.
##### Some months are will not display daily data properly for specific months due to single change in inventory.
![image](https://github.com/jcast6/Inventory-Control/assets/89822103/08899777-4359-4b81-92b8-c40f7eece134)

# Recent updates

# QR code and Barcode scanner 
Integration: Uses the cv2 and pyzbar libraries to scan QR codes and barcodes. On scanning, the system searches the database for the corresponding item and updates the GUI with relevant item information.
![image](https://github.com/jcast6/Inventory-Control/assets/89822103/fad5b674-a697-4d91-87fc-26635a745d28)

## Scanner window opens after code search button is clicked
Scanner Activation: A separate window opens upon clicking the 'Search by Code Scan' button. Camera access Accesses the system's camera for live scanning of QR codes or barcodes.
![image](https://github.com/jcast6/Inventory-Control/assets/89822103/977b7b20-6c76-439b-9501-e1ce4e4ec8e2)

# User can scan a qr code
Scanning Process: The user holds a QR code in front of the camera. On successful scanning, the system decodes the QR code and fetches item details from the database.
![image](https://github.com/jcast6/Inventory-Control/assets/89822103/530d4d44-39fc-496e-861d-4f79b641f5f0)

# Data returned from database when qr code is scanned
Data Handling: The application parses the QR code data to retrieve the item's unique identifier. The GUI does not update to show the scanned item's details, it is currently being worked on. The item details display in the terminal as they are in the database when the qr code is scanned.
![image](https://github.com/jcast6/Inventory-Control/assets/89822103/eae5ab78-a9ee-4f5b-8d48-b08a14c48cb9)


# Coming Fixes:
I will add the qr code and bar code results to the main GUI. This will allow for quick item selection if inventory is large. And the reporting for daily usage will be fixed.







