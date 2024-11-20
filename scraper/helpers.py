import csv
import os

from typing import List


# Function to write a post to CSV
def save_to_csv(post_data_ls: List, filename):
    file_exists = os.path.isfile(filename)

    # Open the CSV file in append mode
    with open(filename, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=post_data_ls[-1].keys())

        # Write the header only if the file doesn't already exist
        if not file_exists:
            writer.writeheader()

        # Write the actual post data
        writer.writerows(post_data_ls)


def save_last_post_id(post_number, filename="scraper/last_post_id.txt"):
    with open(filename, "w") as file:
        file.write(str(post_number))


def load_last_post_id(filename="scraper/last_post_id.txt"):
    try:
        with open(filename, "r") as file:
            return int(file.read())
    except FileNotFoundError:
        return None
