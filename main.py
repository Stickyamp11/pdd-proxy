from functools import wraps
from pipes import quote
import re
from bs4 import BeautifulSoup
from flask import Flask, redirect, render_template_string, request, jsonify, make_response, url_for
import requests

API_KEY = "SECRET_APIKEY_CATS"
DEFAULT_EMPTY_RESPONSE = '''
    <div><span>Not found. No results.</span></div>
'''

DEFAULT_SEARCH_UI = '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PDD HELPER</title>
            <style>
            #searchValue{
                width: 40%;
                height: 20px;
            }
            button{
                padding: 30px;
                font-size: 16px;
            }
            .links_renderer{
                font-size: 40px;
                display:flex;
                flex-direction:column;
                gap:30px;
                
            }
            li{
                margin-top: 20px;
                margin-bottom: 20px;
            }
            li, li a{
                display: flex;
                flex-direction: row;
                gap: 30px;
                align-items: center;
            }
            .country_flag{
                width: 30px;
                height: 30px;
            }
            .episode_info{
                font-size: 40px;
                color: black;

            }

        </style>
        <script>
            function goBack() {
                    window.history.back();
                }
        </script>
        </head>
        <body>
            <h1>Search Page</h1>
            <form action="/doSearch" method="post">
                <label for="searchValue">Search:</label>
                <input type="text" id="searchValue" name="searchValue" required>
                <button type="submit">Search</button>
                <button class="btn-back" onclick="goBack()">Go Back</button>

            </form>
        </body>
        </html>
    '''

app = Flask(__name__, static_folder='public')

# URL of the login page
login_url = 'https://playdede.eu/ajax.php'

# Payload with login credentials
payload = {
    'user': "scrapeme123",
    'pass': "123456",
    '_method': "auth/login"
}

# Create a session object
session_playdede = requests.Session()
# Post the payload to the login page
session_playdede.post(login_url, data=payload)

def requires_login(f):
    @wraps(f)
    def wrapper_login(*args, **kwargs):
        # Check if session cookies are present
        cookies = request.cookies
        # Here you can check specific cookies if needed
        if not cookies or 'pdd_proxy_session' not in cookies:  # Replace 'session_cookie_name' with your actual session cookie name
            return redirect(url_for('login_page'))  # Redirect to the login page
        return f(*args, **kwargs)
    return wrapper_login

@app.route('/')
@requires_login
def home():
    return DEFAULT_SEARCH_UI;

# Function to create a session with a dummy key and return the session cookie
def create_session_with_key(api_key):
    if api_key == API_KEY:
        resp = make_response(redirect('/'))
        resp.set_cookie('pdd_proxy_session', 'I can see you', max_age=60*60*24*31)  # Cookie lasts for 7 days
        return resp
    else:
        return jsonify({"message": "Invalid API key"}), 401

@app.route('/login', methods=['POST'])
def login():
    api_key = request.form.get('api_key')
    return create_session_with_key(api_key)
    
@app.route('/login_page', methods=['GET'])
def login_page():
    # Render the login page
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login</title>
        </head>
        <body>
            <h1>Login</h1>
            <form action="/login" method="post">
                <label for="api_key">API Key:</label>
                <input type="text" id="api_key" name="api_key" required>
                <button type="submit">Login</button>
            </form>
        </body>
        </html>
    ''')

@app.route('/doSearch', methods=['POST'])
@requires_login
def doSearch():
    search_value = request.form.get('searchValue')
    print("This is a message to the console, ", search_value)

    # Ensure the search_value is provided
    if not search_value:
        return jsonify({"error": "No search value provided"}), 400
    
    # Encode the search_value to be URL-safe
    #encoded_search_value = map_string(quote(search_value))
    print("This is a message to the console, ", search_value)
    
    response = session_playdede.get(f"https://playdede.eu/search?s={search_value}")
    # Fetch the profile page content
    content = response.text

     # Parse HTML content with BeautifulSoup
    soup = BeautifulSoup(content, 'lxml')
    
    # Find the element with the class name 'importantElement'
    important_element = soup.find(id=' archive-content')
    
    # Extract the HTML of the important element
    if important_element:
       return DEFAULT_SEARCH_UI + str(important_element)
    #else:
    #    filtered_content = '<p>No important element found.</p>'
    return None

def map_string(input_string):
    return input_string.replace(' ', '+')


@app.route('/pelicula/<param>', methods=['GET'])
@requires_login
def getItem(param):
    search_value = param
    print("This is a message to the console, ", search_value)

    if not search_value:
        return jsonify({"error": "No search value provided"}), 400
    
    print("This is a message to the console, ", search_value)
    
    response = session_playdede.get(f"https://playdede.eu/pelicula/{search_value}")
    content = response.text
    soup = BeautifulSoup(content, 'lxml')
    important_element = soup.find(class_='linkSorter')
    
    if important_element is None:
        return DEFAULT_SEARCH_UI + DEFAULT_EMPTY_RESPONSE;


    list_items = important_element.find_all('li')
    
    new_list_html = '<ul class="custom_links">'
    for item in list_items:
        img_tag = item.find('img')  # Find the img tag
        original_image_strg = img_tag['src'].split('/')[-1]
        if img_tag:
            # Modify the src attribute of the img tag
            img_tag['src'] = url_for('static', filename=f'assets/image/languages/{original_image_strg}')
            img_tag['class'] = img_tag.get('class', '') + 'country_flag'

             # Create a new <span> element
            new_span = soup.new_tag('span', **{'class': 'extra_info'})
            new_span.string = original_image_strg  # Set the text or content for the new <span>

            img_tag.insert_after(new_span)
        
        new_list_html += str(item)
    
    new_list_html += '</ul>'

    if important_element:
       return DEFAULT_SEARCH_UI + str(new_list_html)
    #else:
    return redirect('/')


@app.route('/episodios/<param>/', methods=['GET'])
@requires_login
def getShowEpisode(param):
    search_value = param
    print("This is a message to the console, ", search_value)

    if not search_value:
        return jsonify({"error": "No search value provided"}), 400
    
    print("This is a message to the console, ", search_value)
    
    response = session_playdede.get(f"https://playdede.eu/episodios/{search_value}")
    content = response.text
    soup = BeautifulSoup(content, 'lxml')
    important_element = soup.find(class_='linkSorter')
    
    if important_element is None:
        return DEFAULT_SEARCH_UI + DEFAULT_EMPTY_RESPONSE;

    list_items = important_element.find_all('li')
    
    new_list_html = '<ul class="custom_links">'
    for item in list_items:
        img_tag = item.find('img')  # Find the img tag
        original_image_strg = img_tag['src'].split('/')[-1]
        if img_tag:
            # Modify the src attribute of the img tag
            img_tag['src'] = url_for('static', filename=f'assets/image/languages/{original_image_strg}')
            img_tag['class'] = img_tag.get('class', '') + 'country_flag'

             # Create a new <span> element
            new_span = soup.new_tag('span', **{'class': 'extra_info'})
            new_span.string = original_image_strg  # Set the text or content for the new <span>

            img_tag.insert_after(new_span)
        
        new_list_html += str(item)
    
    new_list_html += '</ul>'

    if important_element:
       return DEFAULT_SEARCH_UI + str(new_list_html)
    #else:
    return redirect('/')



@app.route('/serie/<serieTxt>', methods=['GET'])
@requires_login
def searchShow(serieTxt):
    search_value = serieTxt
    print("This is a message to the console, ", search_value)

    if not search_value:
        return jsonify({"error": "No search value provided"}), 400
        
    response = session_playdede.get(f"https://playdede.eu/serie/{search_value}")
    content = response.text
    soup = BeautifulSoup(content, 'lxml')
    
    # Find all <a> tags with href starting with "/episodios"
    episode_links = soup.find_all('a', href=lambda href: href and href.startswith('/episodios'))
    
    pattern = r'-(\d{1,2}x\d{1,2})/'

    # Create new <a> tags for the links
    new_links_html = '<ul class="episode_links">'
    for link in episode_links:
        href = link['href']
        match = re.search(pattern, href)
        episode_id = match.group(1)
        # Create a new <a> tag with a complete URL or a modified href
        # Create new <a> tag
        new_link = soup.new_tag('a', href=href, **{'class': 'episode_link'})
        new_link.string = link.get_text() or "Episode Link"

        new_span = soup.new_tag('span', **{'class': 'episode_info'})
        new_span.string = episode_id  # Set the text or content for the new <span>

        new_link.append(new_span)

        new_links_html += f'<li>{new_link}</li>'

    
    new_links_html += '</ul>'

    if new_links_html:
       return DEFAULT_SEARCH_UI + str(new_links_html)
    #else:
    return redirect('/')

#def selectMovieItem():


if __name__ == '__main__':
    app.run(debug=True)