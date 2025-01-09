import json

with open("static/assets/content/backup-latest.json", "r") as file:
    blog_data = json.load(file)

body_list = [post['body'] for post in blog_data]

for post in body_list:
    with open("cleaned.txt", "a") as file:
        # Replace actual carriage return (\r) and newline (\n) with empty strings to keep everything in one line
        file.write(post.replace("\r", "").replace("\n", ""))
        file.write("\n")  # Adds a single newline after each post to separate them
