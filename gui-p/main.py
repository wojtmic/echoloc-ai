import requests
import customtkinter as tk
import argparse

class command():
    def __init__(self, name, description, function):
        self.name = name
        self.description = description
        self.function = function

parser = argparse.ArgumentParser(description="Project Oracle - THIS IS A CODENAME, SUBJECT TO CHANGE")
parser.add_argument("--external-ip", type=str, metavar="IP_ADDRESS", help="Force the usage of an external IP address for daemon interaction")
parser.add_argument("--port-override", type=int, metavar="PORT", help="Force the usage of a specific port for daemon interaction")
args = parser.parse_args()

ip = "127.0.0.1"
port = 5609
pinged = False

if args.external_ip:
    print("--external-ip flag detected, ip address will be forced to external")
    ip = args.external_ip

if args.port_override:
    print("--port-override flag detected, port will be forced to the specified value")
    port = args.port_override

print(f"Using IP address: {ip}:{port}")

root = tk.CTk()
root.title("Project Oracle - THIS IS A CODENAME, SUBJECT TO CHANGE")
root.geometry("800x600")
root.resizable(False, False)

class clear_c(command):
    def __init__(self):
        super().__init__("clear", "Clear the chatbox", clear_chatbox)

class ping_c(command):
    def __init__(self):
        super().__init__("ping", "Ping the daemon", ping_command)

class reset_c(command):
    def __init__(self):
        super().__init__("reset", "Reset the conversation", reset_command)

class stop_c(command):
    def __init__(self):
        super().__init__("stop", "Stop the daemon", stop_daemon)

def reset_conversation():
    url = f"http://{ip}:{port}/reset"
    try:
        response = requests.post(url)
        response_data = response.json()
    except:
        print("Reset command failed")
        return False

    if response_data.get('status') == 'ok':
        print("Conversation reset successfully")
        return True
    else:
        print("Reset command failed")
        return False

def reset_command():
    if reset_conversation():
        add_message("Conversation has been reset", "Reset", "royal blue")
    else:
        add_message("Failed to reset the conversation", "Reset", "red")

def stop_daemon():
    url = f"http://{ip}:{port}/stop"
    requests.post(url)
    add_message("Daemon has been stopped", "Stop", "red")
    return True

def ping_daemon():
    global pinged
    url = f"http://{ip}:{port}/ping"

    try:
        response = requests.post(url)
        response_data = response.json()
    except:
        pinged = False
        print("Daemon ping failed")
        return
    
    if response_data.get('status') == 'ok':
        pinged = True
        print("Daemon pinged successfully")
        return True
    else:
        pinged = False
        print("Daemon ping failed")
        return False

def ping_command():
    if ping_daemon():
        add_message("Daemon is reachable", "Ping", "royal blue")
    else:
        add_message("Daemon is not reachable", "Ping", "red")

def send_text(message):
    if not pinged:
        ping_daemon()
        return {"error": "Daemon is not reachable, please try again or use an external ip address/port."}
    url = f"http://{ip}:{port}/chat"
    data = {"message": message}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": "API error occured, please try again or use an external ip address/port."}

def send_text_format(message):
    response = send_text(message)
    if "error" in response:
        add_message(response["error"], "Error", "red")
    else:
        add_message(response["response"], "Oracle", "DodgerBlue2")

def add_message(message="none", title="none", color="gray"):
    msg = tk.CTkFrame(chatbox, fg_color=color)
    msg.pack(side="top", fill="x", padx=5, pady=5)
    tk.CTkLabel(msg, text=title, fg_color=color).pack(side="left", fill="x", padx=5, pady=5)
    tk.CTkLabel(msg, text=message, fg_color=color, wraplength=700, anchor="w").pack(side="left", fill="x", padx=5, pady=5)
    chatbox.after(10, chatbox._parent_canvas.yview_moveto, 1.0)

def clear_chatbox():
    for widget in chatbox.winfo_children():
        widget.destroy()    

commands = [clear_c(), ping_c(), reset_c(), stop_c()]

def button_press():
    if not entry.get():
        return
    # Command system: If message starts with $, treat it as a command and dont send it to the daemon
    if entry.get().startswith("$"):
        add_message(entry.get(), "Command", "SpringGreen2")
        for cmd in commands:
            if entry.get().split(" ")[0] == f"${cmd.name}":
                cmd.function()
                break
    else:
    # When no command is found, proceed normally
        add_message(entry.get(), "You")
        send_text_format(entry.get())
    entry.delete(0, "end")


chatbox = tk.CTkScrollableFrame(root)
chatbox.pack(side="top", fill="both", expand=True)

entry = tk.CTkEntry(root)
entry.pack(side="left", fill="x", padx=0, pady=5, expand=True)
entry.bind("<Return>", lambda x: button_press())

sendbutton = tk.CTkButton(root, text=">", width=1, command=button_press)
sendbutton.pack(side="left", fill="y", padx=0, pady=5)

ping_daemon()
root.mainloop()
