import tkinter as tk
from tkinter import messagebox
from fuzzywuzzy import fuzz

def compare_lists():
    list1 = [phrase.strip() for phrase in entry_list1.get("1.0", tk.END).splitlines() if phrase.strip()]
    list2 = [phrase.strip() for phrase in entry_list2.get("1.0", tk.END).splitlines() if phrase.strip()]

    results = {}
    for phrase2 in list2:
        max_ratio = 0
        for phrase1 in list1:
            ratio = fuzz.partial_ratio(phrase1, phrase2)
            if ratio > max_ratio:
                max_ratio = ratio
        results[phrase2] = max_ratio

    output_text.delete("1.0", tk.END)
    for phrase, ratio in results.items():
        output_text.insert(tk.END, f"{phrase}: {ratio}% match\n")

root = tk.Tk()
root.title("Keyword Phrase Comparison")

label_list1 = tk.Label(root, text="List 1:")
label_list1.grid(row=0, column=0, sticky="w")
entry_list1 = tk.Text(root, height=10, width=40)
entry_list1.grid(row=1, column=0, padx=5)

label_list2 = tk.Label(root, text="List 2:")
label_list2.grid(row=0, column=1, sticky="w")
entry_list2 = tk.Text(root, height=10, width=40)
entry_list2.grid(row=1, column=1, padx=5)

button_compare = tk.Button(root, text="Compare", command=compare_lists)
button_compare.grid(row=2, columnspan=2, pady=5)

output_text = tk.Text(root, height=10, width=40)
output_text.grid(row=3, columnspan=2, padx=5)

root.mainloop()

