<h2 align="center">Blog Boiler Pro</h2>
<p align="center">A lightweight Flask-based boilerplate for creating a blog, utilizing n:point for simple data storage.</p>
<p align="center">
<img src="https://img.shields.io/badge/status-under%20development-blue"/>
<img src="https://img.shields.io/github/license/timonrieger/blog-boiler-pro
">
<img src="https://img.shields.io/github/last-commit/timonrieger/blog-boiler-pro
">
<img src="https://img.shields.io/github/languages/top/timonrieger/blog-boiler-pro">
<img src="https://img.shields.io/badge/code_style-black-black"/>
</p>

<table>
	<tbody>
		<tr>
			<td width="33%">
				Home
				<img src=".github/demo/home.png">
			</td>
         <td width="33%">
				Post Page
				<img src=".github/demo/post.png">
			</td>
			<td width="33%">
				Post Panel
				<img src=".github/demo/panel.png">
			</td>
		</tr>
	</tbody>
</table>


## Intention

This project is a advanced blog implementation, designed for users who prefer a straightforward solution. If you don't require features like user management, an admin interface, or database storage, consider checking out [the lite version](https://github.com/timonrieger/blog-boiler-lite).

## Demo

I [extended and customised](https://github.com/timonrieger/blog) this template myself for [my personal blog](https://blog.timonrieger.de/). Check it out, to see it in action!

## Features

- **Create, Edit, Delete Blog Posts:** Easily manage blog content with intuitive CRUD operations with database storage.
- **Pagination:** View posts with pagination for better navigation and user experience.
- **User-Friendly Text Editor:** A simple and intuitive editor for creating and editing blog posts provided by CKEditor 4.
- **Responsive Design with Bootstrap:** The site automatically adjusts to various screen sizes and devices for seamless usability.
- **Google Translate Support:** Allow posts to be translated from your writing language to other languages. To disable, set the `ENABLE_TRANSLATIONS=False` in `src/config.py`.
- **Collaboration Support:** Share your n:point credentials with co-authors to collaborate on blog posts.
- **Secure, SEO Optimized, and Fast:** Optimized for performance and search engine visibility according to [Checkbot](https://checkbot.io/).
- **Customizable About Page:** Personalize an "About" page for each author to share their story or expertise.
- **User Management:** Basic functionality to manage users: registration, login, anonymous users, and admin management.
- **Admin Privileges:** Assign co-authors the admin role to write, edit, delete their blog posts and all comments. You remain the Super Admin.
- **Commenting System:** Users can now leave comments on posts, with moderation capabilities for the comment author and admins.
- **Soft deletion with undo option**: Deleting posts and comments does not erase them entirely, but rather flag and hide them. 
- **


## Limitations

- No extension or plugin system
- No analytics by default (which I regard as positive)
- No file upload
- No account settings for users ([add an authentication microservice](https://github.com/timonrieger/auth-service))

## Setup

1. **Clone the repository**
   ```
   git clone https://github.com/timonrieger/blog-boiler-pro.git
   ```

2. **Navigate to the project directory**
   ```
   cd blog-boiler-pro
   ```

3. **Create a virtual environment**
   ```
   python -m venv venv
   ```

4. **Activate the virtual environment**
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

5. **Install the required dependencies**
   ```
   pip install -r requirements.txt
   ```

6. Set the required **environment variables** in a `.env` at the root directory. 
   ```
   SECRET_KEY=yoursecretkey
   DB_URI=postgresql://username:password@ahost:port/db # (https://supabase.com/) is free
   ANONYMOUS_ID=1 # register the first user with username "anonymous" or similar for letting users comment anonymously
   SUPER_ID=2 # register yourself, set yourself as admin in the database and define your ID as the Super Admin
   ```

7. **Run the application**
   ```
   python -m main
   ```
   Now go to http://127.0.0.1:5000/ and register the first two users (anonymous and yourself) as mentioned in step 6

## Your First Blog Post
1. **Create a New Blog Post**
   - Go to http://127.0.0.1:5000/new after logging in with your account. This will open the form to write a new blog post.
   - Fill the form with your content.

2. **Add Images to Your Blog Post**
   - Upload your image to the `static/uploads/` directory.
   - To display the image in the blog post, use the following HTML code in your post content or add the URL in CKEditors image interface:
     ```
     <p><img alt="" src="/static/uploads/2.png" style="height:100%; width:100%" /></p>
     ```
   
3. **Set Blog Image URL**
    - For the field `Blog Image URL` field, use the path of the uploaded image, e.g., `/static/uploads/3.png`.


4. **Submit the form**

> **Warning**: Before submitting the form, copy the source HTML code to avoid data loss in case application fails. You can usually go back in the browser to load the filled form again, though.


## Configuration

1. **Add Images**  
   Add the images you want to use in the `static/uploads/` directory with your image files (I personally name the files with [autoincrementing numbers](https://github.com/timonrieger/blog/tree/main/static/uploads)) .

2. **Modify Static Assets**  
   Feel free to modify the following directories and files:
   - `static/assets/img/` (for images)
   - `static/assets/favicon.ico` (for the site favicon)

3. **Modify SEO contents**  
   Replace the contents at the top of each file in the `templates/`
   directory to reflect your content.

4. **Edit author pages**  
   Edit the contents in the author files in `templates/authors/`. Change the name of the file to the username you registered as well as the profile picture in `static/assets/img/`, e.g. John Doe > `john-doe.html` and `john-doe.jpg`

## Endpoints

- **Home**: `/` - View all blog posts.
- **Show Post**: `/<post_title>` - View a single blog post. Add comment logic here as well.
- **New Post**: `/new` - Create a new blog post.
- **Edit Post**: `/<post_title>/edit` - Edit an existing blog post.
- **Delete Post**: `/<post_title>/delete` - Soft deletes a single blog post.
- **Restore Post**: `/<post_title>/delete` - Restores/Unhides a single blog post. 
- **Delete Comment**: `/<post_title>/delete/comment/<int:comment_id>` - Soft deletes a single comment.
- **Restore Comment**: `/<post_title>/restore/comment/<int:comment_id>` - Restores/Unhides a single comment. 
- **Show Author** - `/author/<author>` - View an author's page.
- **Login**: `/login` - Login as a user or anonymously
- **Register**: `/register` - Register a user
- **Logout**: `/logout` - Logout a user

## Roles
There are five types of users:
- Non logged in users: `read` access
- Anonymous user: as above + `write:comment`
- Logged in users: as above + `delete:own_comment`
- Admin user: as above + `write:post`, `edit:own_post`, `delete:own_post`
- Super admin (only one, YOU): full access (can delete, edit, write anything)

## Requirements

- Python 3.x
- The following Python packages (as listed in `requirements.txt`):
   - Bootstrap_Flask==2.2.0
   - Flask_CKEditor==1.0.0
   - Flask_Login==0.6.3
   - Flask-Gravatar==0.5.0
   - Flask_WTF==1.2.1
   - Werkzeug==3.0.0
   - WTForms==3.0.1
   - Flask==2.3.2
   - flask_sqlalchemy==3.1.1
   - SQLAlchemy==2.0.25
   - requests==2.31.0
   - python-dotenv==0.19.1
   - flask-caching==1.10.1
   - gunicorn==20.0.0
   - psycopg2-binary==2.9.10


## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.