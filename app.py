from functools import wraps
from pipes import quote
import re
import subprocess
import time
from bs4 import BeautifulSoup
from flask import Flask, app, redirect, render_template_string, request, jsonify, make_response, url_for
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from seleniumbase import Driver

import pickle

ATTACK_URL = "https://playdede.eu"

#SELENIUM PART

# Prevent downloads by setting an unwritable download directory
prefs = {
    "download.prompt_for_download": False,  # Disable the prompt to download
    "download.directory_upgrade": True,     # Enable directory upgrade (even though it's unwritable)
    "download.default_directory": "/dev/null",  # Set to a non-writable directory
    "download_restrictions": 3,             # Disallow all downloads
}

chrome_options = Options()
chrome_options.add_experimental_option("prefs", prefs)
chrome_options.add_argument("--headless")

# xpaths:
XPATH_LOGIN_USER = "*//form[@action='auth/login']/input[@name='user']";
XPATH_LOGIN_PASS = "*//form[@action='auth/login']/input[@name='pass']";
XPATH_LOGIN_SUBMIT = "*//form[@action='auth/login']/div/button[2]";


#CREATING THE GLOBAL SELENIUM DRIVER INSTANCE
driver = Driver(uc=False, headless=True)

#driver = webdriver.Chrome(options=chrome_options)
driver.implicitly_wait(5)  # seconds

def getInitialLoginCookies():
    # Step 1: Set up the WebDriver and log in to the website
    #driver = webdriver.Chrome(options=chrome_options)
    global driver
    print(ATTACK_URL,"aaaaa")
    driver.get(f"{ATTACK_URL}/login")
    waitSeconds(5);
    print(driver.page_source)

    username = driver.find_element(By.XPATH, XPATH_LOGIN_USER)
    waitSeconds(3);
    password = driver.find_element(By.XPATH, XPATH_LOGIN_PASS)
    waitSeconds(3);
    submitButton = driver.find_element(By.XPATH, XPATH_LOGIN_SUBMIT)
    #closeUnwantedTabsTick(driver,"playdede");
    waitSeconds(3);
    username.send_keys("scrapeme123")
    waitSeconds(3);
    password.send_keys("123456")
    waitSeconds(3);
    clickWithPreventAds(submitButton,driver)
    # Step 2: Save the cookies to a file
    waitSeconds(1);
    cookies = driver.get_cookies()
    with open("cookies.pkl", "wb") as file:
        pickle.dump(cookies, file)

    waitSeconds(1);
    html_source = driver.page_source

    #driver.quit()

def waitSeconds(seconds):
    time.sleep(seconds)

def closeUnwantedTabsTick(driver, match_str = "playdede"):
    current_tabs = driver.window_handles
    for tab in current_tabs:
        driver.switch_to.window(tab)  # Switch to the tab
        current_url = driver.current_url
        print(current_url, "current")
        if match_str not in current_url:
            driver.close()
    remaining_tabs = driver.window_handles
    if remaining_tabs:
        driver.switch_to.window(remaining_tabs[0])

def clickWithPreventAds(element, driver):
    element.click()
    waitSeconds(1)
    #closeUnwantedTabsTick(driver)

def initializeCookiesInDriver():
    global driver
    driver.get(ATTACK_URL)
    # Load cookies from the file
    with open("cookies.pkl", "rb") as file:
        cookies = pickle.load(file)

    # Add each cookie to the browser
    for cookie in cookies:
        driver.add_cookie(cookie)


def callPlaydedeWithCookies(url):
    #driver = webdriver.Chrome(options=chrome_options)
    global driver
    driver.get(url)
    waitSeconds(1)
    html_source = driver.page_source
    #driver.quit()
    return html_source;



# START OF THE FLASK PART
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

@app.after_request
def after_request(response):
    # Optionally log the response details
    app.logger.info(f"Response: {response}")
    return response

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

    if not search_value:
        return "no search_value"
    
    url_to_call = f"{ATTACK_URL}/search?s={search_value}";
    print(url_to_call,"url")
    response = callPlaydedeWithCookies(url_to_call);

    # Fetch the profile page content
    content = response
    # Parse HTML content with BeautifulSoup
    soup = BeautifulSoup(content, 'lxml')

    
    # Find the element with the class name 'importantElement'
    important_element = soup.find(id=' archive-content')
    
    # Extract the HTML of the important element
    if important_element:
        return DEFAULT_SEARCH_UI + str(important_element)
    #else:
    #    filtered_content = '<p>No important element found.</p>'
    return DEFAULT_SEARCH_UI + DEFAULT_EMPTY_RESPONSE



def map_string(input_string):
    return input_string.replace(' ', '+')


@app.route('/pelicula/<param>', methods=['GET'])
@requires_login
def getItem(param):
    search_value = param
    print("This is a message to the console, ", search_value)

    if not search_value:
        return jsonify({"error": "No search value provided"}), 400
        
    response = callPlaydedeWithCookies(f"{ATTACK_URL}/pelicula/{search_value}")
    content = response
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
    
    response = callPlaydedeWithCookies(f"{ATTACK_URL}/episodios/{search_value}")
    content = response
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
        
    response = callPlaydedeWithCookies(f"{ATTACK_URL}/serie/{search_value}")
    content = response
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


if __name__ == '__main__':
    #installGoogleChrome();
    getInitialLoginCookies();
    waitSeconds(1);
    app.run(debug=True, host='0.0.0.0', port=10000)

