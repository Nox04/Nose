import calendar
import os
import platform
import sys
import urllib.request
import psycopg2
import datetime

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from configparser import ConfigParser

# -------------------------------------------------------------
# -------------------------------------------------------------


# Global Variables

driver = None

# whether to download photos or not
download_uploaded_photos = False
download_friends_photos = False

# whether to download the full image or its thumbnail (small size)
# if small size is True then it will be very quick else if its false then it will open each photo to download it
# and it will take much more time
friends_small_size = True
photos_small_size = False

total_scrolls = 3000
current_scrolls = 0
scroll_time = 5

old_height = 0

postgres = None
subject_id = 0


# -------------------------------------------------------------
# -------------------------------------------------------------

def get_facebook_images_url(img_links):
    urls = []

    for link in img_links:

        if link != "None":
            valid_url_found = False
            driver.get(link)

            try:
                while not valid_url_found:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[rel=theater]")))
                    element = driver.find_elements_by_css_selector("a[rel=theater]")

                    div = element[1].find_elements_by_tag_name("div")

                    img = div[0].find_elements_by_tag_name("img")

                    img_url = img[0].get_attribute('src')

                    if img_url.find('.gif') == -1:
                        valid_url_found = True
                        urls.append(img_url)

            except EC.StaleElementReferenceException:
                urls.append(driver.find_element_by_class_name("uiScaledImageContainer").get_attribute('src'))

            except:
                print("Exception (facebook_image_downloader):", sys.exc_info()[0])

        else:
            urls.append("None")

    return urls


# -------------------------------------------------------------
# -------------------------------------------------------------

# takes a url and downloads image from that url
def image_downloader(img_links, folder_name):
    img_names = []

    try:
        parent = os.getcwd()
        try:
            folder = os.path.join(os.getcwd(), folder_name)
            if not os.path.exists(folder):
                os.mkdir(folder)

            os.chdir(folder)
        except:
            print("Error in changing directory")

        for link in img_links:
            img_name = "None"

            if link != "None":
                img_name = (link.split('.jpg')[0]).split('/')[-1] + '.jpg'

                if img_name == "10354686_10150004552801856_220367501106153455_n.jpg":
                    img_name = "None"
                else:
                    try:
                        urllib.request.urlretrieve(link, img_name)
                    except:
                        img_name = "None"

            img_names.append(img_name)

        os.chdir(parent)
    except:
        print("Exception (image_downloader):", sys.exc_info()[0])

    return img_names


# -------------------------------------------------------------
# -------------------------------------------------------------

def check_height():
    new_height = driver.execute_script("return document.body.scrollHeight")
    return new_height != old_height


# -------------------------------------------------------------
# -------------------------------------------------------------

# helper function: used to scroll the page
def scroll():
    global old_height
    current_scrolls = 0

    while True:
        try:
            if current_scrolls == total_scrolls:
                return

            old_height = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            WebDriverWait(driver, scroll_time, 0.05).until(lambda driver: check_height())
            current_scrolls += 1
        except TimeoutException:
            break

    return


# -------------------------------------------------------------
# -------------------------------------------------------------

# --Helper Functions for Posts

def get_status(x):
    status = ""
    try:
        status = x.find_element_by_xpath(".//div[@class='_5pbx userContent']").text
    except:
        try:
            status = x.find_element_by_xpath(".//div[@class='userContent']").text
        except:
            pass
    return status


def get_div_links(x, tag):
    try:
        temp = x.find_element_by_xpath(".//div[@class='_3x-2']")
        return temp.find_element_by_tag_name(tag)
    except:
        return ""


def get_title_links(title):
    link = title.find_elements_by_tag_name('a')
    return link[-1].text, link[-1].get_attribute('href')


def get_title(x):
    title = ""
    try:
        title = x.find_element_by_xpath(".//span[@class='fwb fcg']")
    except:
        try:
            title = x.find_element_by_xpath(".//span[@class='fcg']")
        except:
            try:
                title = x.find_element_by_xpath(".//span[@class='fwn fcg']")
            except:
                pass
    finally:
        return title


def get_post_shared_text(x):
    text = ""
    try:
        element = x.find_element_by_css_selector("div[data-ad-preview=message]")
        inner = element.find_element_by_tag_name("div")
        inner.find_element_by_class_name("see_more_link").click()
        text = inner.find_element_by_tag_name("p").text
    except:
        pass
    finally:
        return text


def get_post_text(x):
    text = ""
    try:
        element = x.find_element_by_css_selector("div[data-ad-preview=message]")
        text = element.find_element_by_tag_name("p").text
    except:
        pass
    finally:
        return text


def get_post_image(x):
    link = ""

    try:
        element = x.find_element_by_css_selector("a[rel=theater]")
        div = element.find_element_by_tag_name("div")
        img = div.find_element_by_tag_name("img")
        link = img.get_attribute('src')
    except:
        try:
            element = x.find_element_by_css_selector("div[data-ad-preview=image-container]")
            div = element.find_element_by_tag_name("div")
            img = div.find_element_by_tag_name("img")
            link = img.get_attribute('src')
        except:
            pass
    finally:
        return link


def get_time(x):
    time = ""
    try:
        time = x.find_element_by_tag_name('abbr').get_attribute('data-utime')
    except:
        pass

    finally:
        return time


def extract_and_write_posts(elements, filename):
    try:
        f = open(filename, "w", newline='\r\n')
        f.writelines(' TIME || TYPE  || TITLE || STATUS  ||   LINKS(Shared Posts/Shared Links etc) ' + '\n' + '\n')

        for x in elements:
            try:
                video_link = " "
                title = " "
                status = " "
                link = ""
                img = " "
                time = " "
                text = " "
                image = ""
                shared_text = " "

                # time
                time = get_time(x)

                # text
                text = get_post_text(x)

                # shared text
                shared_text = get_post_shared_text(x)

                # image
                image = get_post_image(x)

                # title
                title = get_title(x)
                if title.text.find("shared a memory") != -1:
                    x = x.find_element_by_xpath(".//div[@class='_1dwg _1w_m']")
                    title = get_title(x)

                status = get_status(x)
                if title.text == driver.find_element_by_id("fb-timeline-cover-name").text:
                    if status == '':
                        temp = get_div_links(x, "img")
                        if temp == '':  # no image tag which means . it is not a life event
                            link = get_div_links(x, "a").get_attribute('href')
                            type = "status update without text"
                        else:
                            type = 'life event'
                            link = get_div_links(x, "a").get_attribute('href')
                            status = get_div_links(x, "a").text
                    else:
                        type = "status update"
                        if get_div_links(x, "a") != '':
                            link = get_div_links(x, "a").get_attribute('href')

                elif title.text.find(" shared ") != -1:

                    x1, link = get_title_links(title)
                    type = "shared " + x1

                elif title.text.find(" at ") != -1 or title.text.find(" in ") != -1:
                    if title.text.find(" at ") != -1:
                        x1, link = get_title_links(title)
                        type = "check in"
                    elif title.text.find(" in ") != 1:
                        status = get_div_links(x, "a").text

                elif title.text.find(" added ") != -1 and title.text.find("photo") != -1:
                    type = "added photo"
                    link = get_div_links(x, "a").get_attribute('href')

                elif title.text.find(" added ") != -1 and title.text.find("video") != -1:
                    type = "added video"
                    link = get_div_links(x, "a").get_attribute('href')

                else:
                    type = "others"

                if not isinstance(title, str):
                    title = title.text

                status = status.replace("\n", " ")
                title = title.replace("\n", " ")

                image_uri = image_downloader([image], "posts")

                timestamp = datetime.datetime.fromtimestamp(float(time))
                line = str(timestamp) + " || " + str(type) + ' || ' + str(title) + ' || ' + str(status) + ' || ' + str(
                    link) + "\n" + str(text) + " || " + str(shared_text) + "\n"

                text.replace("'", "")
                text.replace('"', '')

                shared_text.replace("'", "")
                shared_text.replace('"', '')

                global subject_id
                sql = "INSERT INTO posts (text, image_url, image_uri, shared_text, created_at, user_id) VALUES ('" + str(text) + "', '" + str(image) + \
                      "', '" + str(image_uri[0]) + "', '" + str(shared_text) + "', '" + str(timestamp) + "', '" + str(subject_id) + "') RETURNING id"

                execute_postgres(sql)
                try:
                    f.writelines(line)
                except:
                    print('Posts: Could not map encoded characters')
            except:
                pass
        f.close()
    except:
        print("Exception (extract_and_write_posts)", "Status =", sys.exc_info()[0])

    return


# -------------------------------------------------------------
# -------------------------------------------------------------


def save_to_file(name, elements, status, current_section):
    """helper function used to save links to files"""

    # status 0 = dealing with friends list
    # status 1 = dealing with photos
    # status 2 = dealing with videos
    # status 3 = dealing with about section
    # status 4 = dealing with posts

    try:

        f = None  # file pointer

        if status != 4:
            f = open(name, 'w', encoding='utf-8', newline='\r\n')

        results = []
        img_names = []

        # dealing with Friends
        if status == 0:

            results = [x.get_attribute('href') for x in elements]
            results = [create_original_link(x) for x in results]

            try:
                if download_friends_photos:

                    if friends_small_size:
                        img_links = [x.find_element_by_css_selector('img').get_attribute('src') for x in elements]
                    else:
                        links = []
                        for friend in results:
                            driver.get(friend)
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "profilePicThumb")))
                            l = driver.find_element_by_class_name("profilePicThumb").get_attribute('href')
                            links.append(l)

                        for i in range(len(links)):
                            if links[i].find('picture/view') != -1:
                                links[i] = "None"

                        img_links = get_facebook_images_url(links)

                    folder_names = ["Friend's Photos", "Following's Photos", "Follower's Photos", "Work Friends Photos",
                                    "College Friends Photos", "Current City Friends Photos", "Hometown Friends Photos"]
                    print("Downloading " + folder_names[current_section])

                    img_names = image_downloader(img_links, folder_names[current_section])
            except:
                print("Exception (Images)", str(status), "Status =", current_section, sys.exc_info()[0])

        # dealing with Photos
        elif status == 1:
            results = [x.get_attribute('href') for x in elements]
            results.pop(0)

            try:
                if download_uploaded_photos:
                    if photos_small_size:
                        background_img_links = driver.find_elements_by_xpath("//*[contains(@id, 'pic_')]/div/i")
                        background_img_links = [x.get_attribute('style') for x in background_img_links]
                        background_img_links = [((x.split('(')[1]).split(')')[0]).strip('"') for x in
                                                background_img_links]
                    else:
                        background_img_links = get_facebook_images_url(results)

                    folder_names = ["Uploaded Photos", "Tagged Photos"]
                    print("Downloading " + folder_names[current_section])

                    img_names = image_downloader(background_img_links, folder_names[current_section])
            except:
                print("Exception (Images)", str(status), "Status =", current_section, sys.exc_info()[0])

        # dealing with Videos
        elif status == 2:
            results = elements[0].find_elements_by_css_selector('li')
            results = [x.find_element_by_css_selector('a').get_attribute('href') for x in results]

            try:
                if results[0][0] == '/':
                    results = [r.pop(0) for r in results]
                    results = [("https://en-gb.facebook.com/" + x) for x in results]
            except:
                pass

        # dealing with About Section
        elif status == 3:
            results = elements[0].text
            f.writelines(results)

        # dealing with Posts
        elif status == 4:
            extract_and_write_posts(elements, name)
            return

        if (status == 0) or (status == 1):
            for i in range(len(results)):
                f.writelines(results[i])
                f.write(',')
                try:
                    f.writelines(img_names[i])
                except:
                    f.writelines("None")
                f.write('\n')

        elif status == 2:
            for x in results:
                f.writelines(x + "\n")

        f.close()

    except:
        print("Exception (save_to_file)", "Status =", str(status), sys.exc_info()[0])

    return


# ----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def scrap_data(id, scan_list, section, elements_path, save_status, file_names):
    """Given some parameters, this function can scrap friends/photos/videos/about/posts(statuses) of a profile"""

    page = []

    if save_status == 4:
        page.append(id)

    for i in range(len(section)):
        page.append(id + section[i])

    for i in range(len(scan_list)):
        try:
            driver.get(page[i])

            if (save_status == 0) or (save_status == 1) or (
                    save_status == 2):  # Only run this for friends, photos and videos

                # the bar which contains all the sections
                sections_bar = driver.find_element_by_xpath("//*[@class='_3cz'][1]/div[2]/div[1]")

                if sections_bar.text.find(scan_list[i]) == -1:
                    continue

            if save_status != 3:
                scroll()

            data = driver.find_elements_by_xpath(elements_path[i])

            save_to_file(file_names[i], data, save_status, i)

        except:
            print("Exception (scrap_data)", str(i), "Status =", str(save_status), sys.exc_info()[0])


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def create_original_link(url):
    if url.find(".php") != -1:
        original_link = "https://en-gb.facebook.com/" + ((url.split("="))[1])

        if original_link.find("&") != -1:
            original_link = original_link.split("&")[0]

    elif url.find("fnr_t") != -1:
        original_link = "https://en-gb.facebook.com/" + ((url.split("/"))[-1].split("?")[0])
    elif url.find("_tab") != -1:
        original_link = "https://en-gb.facebook.com/" + (url.split("?")[0]).split("/")[-1]
    else:
        original_link = url

    return original_link


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def scrap_profile(ids):
    folder = os.path.join(os.getcwd(), "Data")

    if not os.path.exists(folder):
        os.mkdir(folder)

    os.chdir(folder)

    # execute for all profiles given in input.txt file
    for id in ids:

        driver.get(id)
        url = driver.current_url
        id = create_original_link(url)

        print("\nScraping:", id)

        try:
            if not os.path.exists(os.path.join(folder, id.split('/')[-1])):
                os.mkdir(os.path.join(folder, id.split('/')[-1]))
                sql = "INSERT INTO subjects (name) VALUES ('" + id.split('/')[-1] + "') RETURNING id"
                global subject_id
                subject_id = execute_postgres(sql)
            else:
                print("A folder with the same profile name already exists."
                      " Kindly remove that folder first and then run this code.")
                continue
            os.chdir(os.path.join(folder, id.split('/')[-1]))
        except:
            print("Some error occurred in creating the profile directory.")
            continue

        # ----------------------------------------------------------------------------
        print("----------------------------------------")
        print("Friends..")
        # setting parameters for scrap_data() to scrap friends
        scan_list = ["All", "Following", "Followers", "Work", "College", "Current City", "Hometown"]
        section = ["/friends", "/following", "/followers", "/friends_work", "/friends_college", "/friends_current_city",
                   "/friends_hometown"]
        elements_path = ["//*[contains(@id,'pagelet_timeline_medley_friends')][1]/div[2]/div/ul/li/div/a",
                         "//*[contains(@class,'_3i9')][1]/div/div/ul/li[1]/div[2]/div/div/div/div/div[2]/ul/li/div/a",
                         "//*[contains(@class,'fbProfileBrowserListItem')]/div/a",
                         "//*[contains(@id,'pagelet_timeline_medley_friends')][1]/div[2]/div/ul/li/div/a",
                         "//*[contains(@id,'pagelet_timeline_medley_friends')][1]/div[2]/div/ul/li/div/a",
                         "//*[contains(@id,'pagelet_timeline_medley_friends')][1]/div[2]/div/ul/li/div/a",
                         "//*[contains(@id,'pagelet_timeline_medley_friends')][1]/div[2]/div/ul/li/div/a"]
        file_names = ["All Friends.txt", "Following.txt", "Followers.txt", "Work Friends.txt", "College Friends.txt",
                      "Current City Friends.txt", "Hometown Friends.txt"]
        save_status = 0

        scrap_data(id, scan_list, section, elements_path, save_status, file_names)
        print("Friends Done")
        # ----------------------------------------------------------------------------

        print("----------------------------------------")
        print("Photos..")
        print("Scraping Links..")
        # setting parameters for scrap_data() to scrap photos
        scan_list = ["'s Photos", "Photos of"]
        section = ["/photos_all", "/photos_of"]
        elements_path = ["//*[contains(@id, 'pic_')]"] * 2
        file_names = ["Uploaded Photos.txt", "Tagged Photos.txt"]
        save_status = 1

        scrap_data(id, scan_list, section, elements_path, save_status, file_names)
        print("Photos Done")

        # ----------------------------------------------------------------------------

        print("----------------------------------------")
        print("Videos:")
        # setting parameters for scrap_data() to scrap videos
        scan_list = ["'s Videos", "Videos of"]
        section = ["/videos_by", "/videos_of"]
        elements_path = ["//*[contains(@id, 'pagelet_timeline_app_collection_')]/ul"] * 2
        file_names = ["Uploaded Videos.txt", "Tagged Videos.txt"]
        save_status = 2

        scrap_data(id, scan_list, section, elements_path, save_status, file_names)
        print("Videos Done")
        # ----------------------------------------------------------------------------

        print("----------------------------------------")
        print("About:")
        # setting parameters for scrap_data() to scrap the about section
        scan_list = [None] * 7
        section = ["/about?section=overview", "/about?section=education", "/about?section=living",
                   "/about?section=contact-info", "/about?section=relationship", "/about?section=bio",
                   "/about?section=year-overviews"]
        elements_path = ["//*[contains(@id, 'pagelet_timeline_app_collection_')]/ul/li/div/div[2]/div/div"] * 7
        file_names = ["Overview.txt", "Work and Education.txt", "Places Lived.txt", "Contact and Basic Info.txt",
                      "Family and Relationships.txt", "Details About.txt", "Life Events.txt"]
        save_status = 3

        scrap_data(id, scan_list, section, elements_path, save_status, file_names)
        print("About Section Done")

        # ----------------------------------------------------------------------------
        print("----------------------------------------")
        print("Posts:")
        # setting parameters for scrap_data() to scrap posts
        scan_list = [None]
        section = []
        elements_path = ["//div[@class='_4-u2 mbm _4mrt _5jmm _5pat _5v3q _4-u8']"]

        file_names = ["Posts.txt"]
        save_status = 4

        scrap_data(id, scan_list, section, elements_path, save_status, file_names)
        print("Posts(Statuses) Done")
        print("----------------------------------------")
    # ----------------------------------------------------------------------------
    #close_postgres()
    print("\nProcess Completed.")

    return


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

def login(email, password):
    """ Logging into our own profile """

    try:
        global driver

        options = Options()

        #  Code to disable notifications pop up of Chrome Browser
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--mute-audio")
        # options.add_argument("headless")

        try:
            if platform.system() == 'Linux':
                driver = webdriver.Chrome(executable_path="./chromedriver", options=options)
            else:
                driver = webdriver.Chrome(executable_path="./chromedriver.exe", options=options)
        except:
            print("Kindly replace the Chrome Web Driver with the latest one from"
                  " http://chromedriver.chromium.org/downloads")
            exit()

        driver.get("https://en-gb.facebook.com")
        driver.maximize_window()

        # filling the form
        driver.find_element_by_name('email').send_keys(email)
        driver.find_element_by_name('pass').send_keys(password)

        # clicking on login button
        driver.find_element_by_id('loginbutton').click()

    except Exception as e:
        print("There's some error in log in.")
        print(sys.exc_info()[0])
        exit()


# load params from config file
def config(section, filename):
    parser = ConfigParser()
    parser.read(filename)

    values = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            values[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))
    return values


# connect to postgresql
def connect_postgres():
    global postgres
    params = config("postgresql", "config.ini")
    print("\nConnecting to postgres...")
    postgres = psycopg2.connect(**params)
    print("\nConnected to postgres.")


# close postgresql connection
def close_postgres():
    global postgres
    postgres.close()
    print("\nDatabase connection closed.")


# insert into postgresql table
def execute_postgres(sql):
    try:
        global postgres
        cursor = postgres.cursor()
        cursor.execute(sql)
        record_id = cursor.fetchone()[0]
        postgres.commit()

        cursor.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print("\n" + error)
    finally:
        return record_id

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


def main():
    ids = ["https://en-gb.facebook.com/" + line.split("/")[-1] for line in open("input.txt", newline='\n')]

    if len(ids) > 0:
        connect_postgres()
        print("\nStarting Scraping...")

        params = config("facebook", "config.ini")
        login(**params)
        scrap_profile(ids)
        driver.close()
    else:
        print("Input file is empty..")


# -------------------------------------------------------------
# -------------------------------------------------------------
# -------------------------------------------------------------


# get things rolling
main()
