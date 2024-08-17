import json
import asyncio
import tkinter as tk
from tkinter import ttk, messagebox
from contextlib import asynccontextmanager

import aiofiles


def draw(auth_file_path):
    root = tk.Tk()
    root.title("Регистрация")

    entry_frame = ttk.Frame(root)
    entry_frame.pack(pady=20)

    username_label = ttk.Label(entry_frame, text="Имя пользователя:")
    username_label.grid(row=0, column=0, padx=5, pady=5)

    username_entry = ttk.Entry(entry_frame)
    username_entry.grid(row=0, column=1, padx=5, pady=5)

    register_button = ttk.Button(
        root,
        text="Зарегистрироваться",
        command=lambda: asyncio.run(
            register(root, username_entry.get(), auth_file_path)
        )
    )
    register_button.pack(pady=10)

    status_label = ttk.Label(root, text="")
    status_label.pack()

    root.mainloop()


def escape_stickiness_removed(text):
    return text.replace("\\n", " ").strip()


@asynccontextmanager
async def create_chat_connection(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def register(root, username, auth_file_path):
    try:
        async with create_chat_connection("minechat.dvmn.org", 5050) as (reader, writer):
            data = await reader.read(100)

            writer.write("\n".encode())

            data = await reader.read(100)

            writer.write((escape_stickiness_removed(username) + "\n").encode())

            response = await reader.readline()

            auth_data = json.loads(response.decode().strip())

            writer.close()

            async with aiofiles.open(auth_file_path, 'w') as file:
                await file.write(json.dumps(auth_data))

            messagebox.showinfo("Регистрация", "Регистрация прошла успешно!")
            root.destroy()

    except Exception as e:
        messagebox.showerror("Регистрация", f"Произошла ошибка: {e}")
        root.destroy()
