import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageDraw, ImageFont, ImageTk
import ctypes
import os
import sys
import webbrowser  # For opening the Instagram link

import traceback  # For detailed exception traceback

# Ensure the script operates relative to its own directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def resource_path(relative_path):
    """Get absolute path to resource."""
    base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def create_cursor(emoji_image_path, hotspot_x, hotspot_y):
    """Create a cursor file from the emoji image with adjusted hotspot."""
    try:
        print(f"Creating cursor from image: {emoji_image_path}")  # Debugging print

        # Load the emoji image
        img = Image.open(emoji_image_path).convert('RGBA')
        img = img.resize((64, 64), Image.LANCZOS)

        # Save the image to a bytes buffer in PNG format
        from io import BytesIO
        image_bytes = BytesIO()
        img.save(image_bytes, format='PNG')
        image_bytes = image_bytes.getvalue()

        # Build the .cur file with hotspot
        cursor_path = os.path.join(os.getenv('TEMP'), "emoji_cursor.cur")
        with open(cursor_path, 'wb') as f:
            # Write the cursor header
            f.write(b'\x00\x00')  # Reserved
            f.write(b'\x02\x00')  # Image type (2 for cursor)
            f.write(b'\x01\x00')  # Number of images

            # Image entry
            width = 64
            height = 64

            print(f"Hotspot coordinates: ({hotspot_x}, {hotspot_y})")

            f.write(bytes([width % 256]))  # Image width
            f.write(bytes([height % 256]))  # Image height
            f.write(b'\x00')  # Number of colors (0 if >=8bpp)
            f.write(b'\x00')  # Reserved
            f.write(hotspot_x.to_bytes(2, byteorder='little'))  # Hotspot X
            f.write(hotspot_y.to_bytes(2, byteorder='little'))  # Hotspot Y
            f.write(len(image_bytes).to_bytes(4, byteorder='little'))  # Image size
            f.write((22).to_bytes(4, byteorder='little'))  # Offset to image data (fixed header size)

            # Write the image data
            f.write(image_bytes)

        print(f"Cursor file saved at: {cursor_path}")  # Debugging print
        return cursor_path
    except Exception as e:
        messagebox.showerror("Error", f"Failed to create cursor: {e}")
        print(f"Failed to create cursor: {e}")  # Debugging print
        traceback.print_exc()
        return None

def set_cursor(cursor_path):
    """Set the system cursor to the newly created cursor."""
    try:
        print(f"Setting cursor from file: {cursor_path}")  # Debugging print
        cursor = ctypes.windll.user32.LoadImageW(
            0, cursor_path, 2, 0, 0, 0x00000010)
        if cursor == 0:
            messagebox.showerror("Cursor Error", "Failed to load cursor.")
            print("Failed to load cursor.")  # Debugging print
            return False
        ctypes.windll.user32.SetSystemCursor(cursor, 32512)
        messagebox.showinfo("Success", "Cursor changed successfully!")
        print("Cursor changed successfully!")  # Debugging print
        return True
    except Exception as e:
        messagebox.showerror("Cursor Error", f"Failed to set cursor: {e}")
        print(f"Failed to set cursor: {e}")  # Debugging print
        traceback.print_exc()
        return False

def reset_cursor():
    """Reset the system cursor to the default."""
    try:
        print("Resetting cursor to default.")  # Debugging print
        ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, 0, 0)
        messagebox.showinfo("Reset", "Cursor reset to default.")
        print("Cursor reset to default.")  # Debugging print
    except Exception as e:
        messagebox.showerror("Reset Error", f"Failed to reset cursor: {e}")
        print(f"Failed to reset cursor: {e}")  # Debugging print
        traceback.print_exc()

def select_emoji():
    """Open a window to select an emoji and set hotspot."""
    try:
        print("Opening emoji selection window.")  # Debugging print
        emoji_window = tk.Toplevel(app)
        emoji_window.title("Select an Emoji")
        emoji_window.geometry("750x600")
        emoji_window.resizable(False, False)

        # Set background color for contrast
        emoji_window.configure(bg="#e6e6e6")  # Light gray background

        # Main frame to hold everything with padding and border
        main_frame = tk.Frame(emoji_window, bg="#e6e6e6", bd=2, relief="ridge")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left frame for emojis with background color
        left_frame = tk.Frame(main_frame, bg="#f0f0f0")  # Slightly lighter gray
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5), pady=5)

        # Right frame for hotspot selection with background color
        right_frame = tk.Frame(main_frame, bg="#ffffff")  # White background
        right_frame.pack(side="right", fill="y", padx=(5, 0), pady=5)

        # Canvas and scrollbar for emojis
        canvas = tk.Canvas(left_frame, bg="#f0f0f0", highlightthickness=0)
        scrollbar = tk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Mouse wheel scroll implementation
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        # Bind the mouse wheel to the canvas
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Hotspot selection canvas with border
        hotspot_canvas_size = 200
        hotspot_canvas = tk.Canvas(right_frame, width=hotspot_canvas_size, height=hotspot_canvas_size,
                                   bg="white", highlightthickness=1, highlightbackground="black")
        hotspot_canvas.pack(pady=10)

        # Instructions label
        instructions = tk.Label(right_frame, text="Click to set hotspot", bg="#ffffff")
        instructions.pack()

        # Variable to store hotspot coordinates
        hotspot_coords = {'x': 0, 'y': 0}

        # Variable to store selected emoji path and image
        selected_emoji_path = [None]
        selected_emoji_photo = [None]  # To prevent garbage collection

        # Function to handle click on hotspot canvas
        def hotspot_click(event):
            if selected_emoji_path[0] is None:
                messagebox.showwarning("No Image Selected", "Please select an image first.")
                return
            # Clear previous hotspot indicator
            hotspot_canvas.delete("hotspot_indicator")
            # Draw a cross at the clicked position
            hotspot_canvas.create_line(event.x - 5, event.y, event.x + 5, event.y, fill="red", tags="hotspot_indicator")
            hotspot_canvas.create_line(event.x, event.y - 5, event.x, event.y + 5, fill="red", tags="hotspot_indicator")
            # Save the coordinates
            hotspot_coords['x'] = int(event.x / hotspot_canvas_size * 64)
            hotspot_coords['y'] = int(event.y / hotspot_canvas_size * 64)
            print(f"Hotspot set at ({hotspot_coords['x']}, {hotspot_coords['y']})")

        # Bind the click event to the hotspot canvas
        hotspot_canvas.bind("<Button-1>", hotspot_click)

        # Prepare the list of emoji image paths
        emoji_folder = resource_path("emojis")
        print(f"Emoji folder path: {emoji_folder}")  # Debugging print

        if not os.path.exists(emoji_folder):
            print(f"Emoji folder does not exist: {emoji_folder}")
            messagebox.showerror("Error", f"Emoji folder does not exist: {emoji_folder}")
            return
        else:
            print(f"Emoji folder found: {emoji_folder}")

        emoji_files = os.listdir(emoji_folder)
        print(f"Found {len(emoji_files)} files in emoji folder.")  # Debugging print

        emoji_image_paths = [os.path.join(emoji_folder, f) for f in emoji_files if f.lower().endswith('.png')]
        print(f"Found {len(emoji_image_paths)} PNG emoji images.")  # Debugging print

        if not emoji_image_paths:
            print("No PNG images found in emoji folder.")
            messagebox.showerror("Error", "No PNG images found in emoji folder.")
            return

        # Function to set selected emoji and update hotspot canvas
        def select_emoji_image(e_path, e_img):
            selected_emoji_path[0] = e_path
            # Resize the image to fit the hotspot canvas
            resized_img = e_img.resize((hotspot_canvas_size, hotspot_canvas_size), Image.LANCZOS)
            selected_photo = ImageTk.PhotoImage(resized_img)
            selected_emoji_photo[0] = selected_photo  # Keep reference
            hotspot_canvas.delete("all")
            hotspot_canvas.create_image(0, 0, anchor="nw", image=selected_photo)
            # Clear hotspot indicator
            hotspot_coords['x'] = 0
            hotspot_coords['y'] = 0
            hotspot_canvas.delete("hotspot_indicator")
            print(f"Selected image: {e_path}")

        columns = 8
        for idx, emoji_path in enumerate(emoji_image_paths):
            row = idx // columns
            col = idx % columns
            try:
                print(f"Loading emoji image: {emoji_path}")  # Debugging print
                # Load the emoji image
                emoji_img = Image.open(emoji_path)
                emoji_img_resized = emoji_img.resize((32, 32), Image.LANCZOS)
                photo = ImageTk.PhotoImage(emoji_img_resized)

                emj_button = tk.Button(
                    scrollable_frame,
                    image=photo,
                    command=lambda e_path=emoji_path, e_img=emoji_img: select_emoji_image(e_path, e_img),
                    bg="#f0f0f0",
                    relief="flat"
                )
                emj_button.image = photo  # Keep a reference to prevent garbage collection
                emj_button.grid(row=row, column=col, padx=5, pady=5)
            except Exception as e:
                print(f"Error loading image {emoji_path}: {e}")  # Debugging print
                traceback.print_exc()

        # Button to use your own image
        def browse_image():
            file_path = filedialog.askopenfilename(
                title="Select an Image",
                filetypes=[("PNG Images", "*.png")]
            )
            if file_path:
                try:
                    user_img = Image.open(file_path)
                    # Resize for display
                    user_img_resized_display = user_img.resize((32, 32), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(user_img_resized_display)

                    # Create a button for the user's image
                    emj_button = tk.Button(
                        scrollable_frame,
                        image=photo,
                        command=lambda e_path=file_path, e_img=user_img: select_emoji_image(e_path, e_img),
                        bg="#f0f0f0",
                        relief="flat"
                    )
                    emj_button.image = photo  # Keep a reference
                    # Place it at the beginning
                    emj_button.grid(row=0, column=0, padx=5, pady=5)

                    print(f"User selected image: {file_path}")
                    # Automatically select the image
                    select_emoji_image(file_path, user_img)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load image: {e}")
                    print(f"Failed to load user image: {e}")
                    traceback.print_exc()

        browse_button = tk.Button(left_frame, text="Use Your Own Image", command=browse_image)
        browse_button.pack(pady=5)

        # Apply button
        def apply_cursor():
            if selected_emoji_path[0] is None:
                messagebox.showwarning("No Image Selected", "Please select an image first.")
                return
            cursor_path = create_cursor(selected_emoji_path[0], hotspot_coords['x'], hotspot_coords['y'])
            if cursor_path:
                set_cursor(cursor_path)
            emoji_window.destroy()

        apply_button = tk.Button(right_frame, text="Apply", command=apply_cursor, width=15)
        apply_button.pack(pady=10)

        # Program credit at the bottom
        def open_instagram(event):
            webbrowser.open_new("https://www.instagram.com/frankly_everything/")

        credit_label = tk.Label(emoji_window, text="Emoji Cursor by Frankly Everything", bg="#e6e6e6", cursor="hand2")
        credit_label.pack(side="bottom", pady=5)
        credit_label.bind("<Button-1>", open_instagram)

    except Exception as e:
        print(f"An error occurred in select_emoji: {e}")  # Debugging print
        traceback.print_exc()
        messagebox.showerror("Error", f"An error occurred: {e}")

# Create the main application window
app = tk.Tk()
app.title("Emoji Cursor Selector")
app.geometry("300x200")
app.resizable(False, False)

# Set background color
app.configure(bg="#e6e6e6")

# Center the window
app.eval('tk::PlaceWindow . center')

print(f"Current working directory: {os.getcwd()}")  # Debugging print

# Add buttons to the GUI
select_button = tk.Button(app, text="Select Emoji Cursor", command=select_emoji, width=25)
select_button.pack(pady=(30, 10))

reset_button = tk.Button(app, text="Reset Cursor to Default", command=reset_cursor, width=25)
reset_button.pack(pady=10)

# Program credit at the bottom
def open_instagram_main(event):
    webbrowser.open_new("https://www.instagram.com/frankly_everything/")

credit_label_main = tk.Label(app, text="Emoji Cursor by Frankly Everything", bg="#e6e6e6", cursor="hand2")
credit_label_main.pack(side="bottom", pady=5)
credit_label_main.bind("<Button-1>", open_instagram_main)

# Run the application
app.mainloop()
