<h2 align="center">Blog Boiler Pro</h2>
<p align="center">A lightweight Flask-based boilerplate for creating an advanced blog with database storage.</p>
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
			<td width="14.3%">
				Home
				<img src=".github/demo/home.png">
			</td>
         <td width="14.3%">
				Login
				<img src=".github/demo/login.png">
			</td>
         <td width="14.3%">
				Register
				<img src=".github/demo/register.png">
			</td>
         <td width="14.3%">
				Post Page
				<img src=".github/demo/post.png">
			</td>
			<td width="14.3%">
				Comment View
				<img src=".github/demo/comments.png">
			</td>
         <td width="14.3%">
				Post Panel
				<img src=".github/demo/panel.png">
			</td>
         <td width="14.3%">
				Author Page
				<img src=".github/demo/author.png">
			</td>
		</tr>
	</tbody>
</table>


## Intention

This project is a advanced blog implementation, designed for users who prefer a more complete solution. If you don't require features like user management, an admin interface, or database storage, consider checking out [the lite version](https://github.com/timonrieger/blog-boiler-lite).

## Demo

I [extended and customised](https://github.com/timonrieger/blog) this template myself for [my personal blog](https://blog.timonrieger.de/). Check it out, to see it in action!

## Features

- **Create, Edit, Draft, Delete Blog Posts:** Easily manage blog content with intuitive CRUD operations with database storage.
- **Pagination:** View posts with pagination for better navigation and user experience.
- **User-Friendly Text Editor:** A simple and intuitive editor for creating and editing blog posts provided by CKEditor 4.
- **Responsive Design with Bootstrap:** The site automatically adjusts to various screen sizes and devices for seamless usability.
- **Collaboration Support:** Give admin access to co-authors to collaborate on the blog.
- **Secure, SEO Optimized, and Fast:** Optimized for performance and search engine visibility according to [Checkbot](https://checkbot.io/).
- **Customizable About Page:** Personalize an "About" page for each author to share their story or expertise.
- **User Management:** Basic functionality to manage users: registration, login, anonymous users, and admin management.
- **Admin Privileges:** Assign co-authors the admin role to write, edit, delete their blog posts and all comments. You remain the Super Admin.
- **Multi Language Support:** Use the language your are writing in for the whole application (<a href="#multi-language-support">Read on</a>)
- **Commenting System:** Users can publish and edit comments on posts, with moderation capabilities for the comment author and admins.
- **Soft deletion with undo option**: Deleting posts and comments does not erase them entirely, but rather flag and hide them. 
- **Filter by tag, author and year**: Posts can be filtered by tag, author and year to narrow down the results.
- **RSS Support**: Auto-generated RSS feed, which users can subscribe to with their RSS-Reader to receive new posts comfortably.
- **HTTP/Browser Caching Strategy**: Invalidates the browser cache for changed content, else uses the cached version.

## Limitations

- No extension or plugin system
- No analytics by default (which I regard as positive)
- No file upload
- No account settings for users, like confirmation email or password reset ([add an authentication microservice](https://github.com/timonrieger/auth-service))

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
   DB_URI=postgresql://username:password@host:port/db
   ANONYMOUS_ID=1 # register the first user with username "anonymous" or similar for letting users comment anonymously
   SUPER_ID=2 # register yourself, set as admin in the database and define your ID in the `.env`
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
   Add the images you want to use in the `static/uploads/` directory with your image files (I personally name the files with [autoincrementing numbers](https://github.com/timonrieger/blog/tree/main/static/uploads)).

2. **Modify Static Assets**  
   Feel free to modify the following directories and files:
   - `static/assets/img/` (for images)
   - `static/assets/favicon.ico` (for the site favicon)

3. **Modify SEO contents**  
   Replace the contents at the top of each file in the `templates/`
   directory to reflect your content.

4. **Edit author pages**  
   Edit the contents in the author files in `templates/authors/`. Change the name of the file to the username you registered as well as the profile picture in `static/assets/img/`, e.g. John Doe > `john-doe.html` and `john-doe.jpg`

5. **Update the `src/config.py` configuration file
   - `LANGUAGE`: Your blog should be in a different language than English? <a href="#multi-language-support">start here</a>
   - `DISPLAY_READING_TIME`: Show the approximate reading time on each post (True/False).
   - `DISPLAY_EDIT_DATE`: Show the edit date if you edited the post body (True/False).
   - `DRAFT_ON_DEFAULT`: Sets the checkbox to publish as draft in the post form on default (True/False).
   - `TIMEZONE_OFFSET`: Set the offset to UTC (e.g. for New York -5) (± number)
   - `DATE_FORMAT`: The format for dates (used everywhere except comments) (valid datetime format).
   - `DATE_FORMAT_LONG`: The format for dates (used in comments) (valid datetime format).

      => [Datetime Format Guide](https://www.pythonmorsels.com/strptime/)
   - `CHECK_EMAIL`: Whether to check if the email is valid/delivarable (True/False)
   - `IMAGES_FOLDER`: The path to your images folder (path).
   - `POSTS_PER_PAGE`: Number of posts on the home route before displaying pagination buttons (integer).
   - `BLOG_NAME`: The name of your blog (string).
   - `BLOG_TITLE`: The title that shows up on search machines for the home page (string).
   - `BLOG_DESCRIPTION`: The description that shows up on search machines for the home page (string).



## Multi-Language Support

The blog currently supports **English** (`en`) and **German** (`de`).

When setting up your blog, you can define the default language for your application. The intent is not for users to switch between languages dynamically but to ensure that application texts align with the language you are writing in.

### Contribute a New Language

If you'd like to contribute a new language you're fluent in, feel free to submit a Pull Request (PR) containing the translated `message.po` file for that language. Your contribution is highly appreciated! Note that there are approximately **75 phrases/sentences** to translate, making it a manageable task.

### Using a Different Language Without Translating

If you'd rather use a different language without contributing translations, start by following the instructions in the section [Compile the Language](#compile-the-language).

### Translating a Language

If you'd like to help translate, follow these steps:

1. Navigate to the project root.

   ```bash
   cd /path/to/project

Navigate to the project root.

### Get all languages available
>Note: may be not fully translated
```bash
find translations -mindepth 1 -maxdepth 1 -type d
```

### Get all strings for translation
Extracts all translateable strings from the `.html` and `.py` files into `message.pot`.
```bash
pybabel extract -F babel.cfg -k lazy_gettext -o translations/messages.pot .
```

### a) Initialize a language (ONLY ONCE)
```bash
pybabel init -i translations/messages.pot -d translations -l LANG_LOCAL
```

### b) Update a language
```bash
pybabel update -i translations/messages.pot -d translations
```

### Translate 
We have to translate manually, but you can start out with [Deepl in VSCode](https://marketplace.visualstudio.com/items?itemName=soerenuhrbach.vscode-deepl). We use common not highly formal language.

Fill the `msgstr ""` in the `LANG_LOCAL/LC_MESSAGES/messages.po` with the translation. Check existing languages if you're lost.
`⌘F` and search for the term fuzzy and delete it ([docs](https://python-babel.github.io/flask-babel/#translating-applications)).

### Compile the language
Compiles all languages for usage.
```bash
pybabel compile -f -d translations
```

### Apply and reload
In `src/config.py` change `LANGUAGE` to the language locale you want, then run:
```bash
python -m main
```

## Roles
There are five types of users:
- Non logged in users: `read` access
- Anonymous user: as above + `write:comment`
- Logged in users: as above + `delete:own_comment`
- Admin user: as above + `write:post`, `edit:own_post`, `delete:own_post`
- Super admin (only one, YOU): full access (can delete, edit, write anything)

## Endpoints

- **Home**: `/` - View all blog posts.
- **Show Post**: `/<post_title>` - View a single blog post. Add comment logic here as well.
- **New Post**: `/new` - Create a new blog post.
- **Edit Post**: `/<post_title>/edit` - Edit an existing blog post.
- **Delete Post**: `/<post_title>/delete` - Soft deletes a single blog post.
- **Restore Post**: `/<post_title>/restore` - Restores/Unhides a single blog post. 
- **Delete Comment**: `/<post_title>/delete/comment/<int:comment_id>` - Soft deletes a single comment.
- **Restore Comment**: `/<post_title>/restore/comment/<int:comment_id>` - Restores/Unhides a single comment. 
- **Show Author** - `/author/<author>` - View an author's page.
- **Login**: `/login` - Login as a user or anonymously.
- **Register**: `/register` - Register a user.
- **Logout**: `/logout` - Logout a user.
- **RSS**: `/feed`, `/rss` and `/rss.xml` - Load blog feed users can subscribe to.

## Requirements

- Python 3.x
- The following Python packages (as listed in `requirements.txt`)
- A hosting service to deploy your blog to ([Vercel](https://vercel.com/), [Render](https://render.com/) etc.)
- A database ([Supabase](https://supabase.com/) is free)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.