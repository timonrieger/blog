import os
import hashlib

def parse_title(raw_title):
   '''Converts the post title to a url string'''
   return raw_title.lower().replace(' ', '-')

def find_post(title, post_model, user_model):
  '''Uses a lower case title combined with hyphens and returns the corresponding BlogPost object in the database'''
  all_posts = post_model.query.all()
  post_list = [item for item in all_posts if parse_title(item.title) == title]
  if not post_list:
    raise NotFound()
  post = post_list[0]
  post.author = user_model.query.filter_by(id=post.author_id).first()
  return post


def add_author(list, user_model):
  '''Maps the author id to the User object and attaches the username to each item in the list (BlogPost or BlogComment)'''
  authors = [post.author_id for post in list]
  usernames = user_model.query.filter(user_model.id.in_(authors)).all()
  user_dict = {user.id: user for user in usernames}
  list_with_authors = []
  for item in list:
      item.author = user_dict.get(item.author_id, "")
      list_with_authors.append(item)
  return list_with_authors


def random_gravatar_url(size=80):
    """Generate a unique Gravatar-like URL using a random value."""
    random_bytes = os.urandom(16)
    random_hash = hashlib.md5(random_bytes).hexdigest()
    return f"{random_hash}@mailinator.com"

  