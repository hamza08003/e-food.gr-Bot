from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
# from faker import Faker
import pandas as pd
import random
import json
import time
import os


class ProfileCreator:
    def __init__(self, website_url):
        self.website_url = website_url
        self.driver = None
        # self.fake = Faker('el_GR')
        # self.password = password
        self.cookies_dir = "profile_cookies"
        self.current_profile_index = 0
        
        # create cookies directory if it doesn't exist
        if not os.path.exists(self.cookies_dir):
            os.makedirs(self.cookies_dir)


    def load_user_agents(self):
        """
        Load user agents from JSON file
        """
        try:
            with open('user_agents.json', 'r') as f:
                data = json.load(f)
                return data['user_agents']
        except Exception as e:
            print(f"Error loading user agents: {e}")
            return []


    def get_next_user_agent(self):
        """
        Get next user agent in rotation
        """
        if not hasattr(self, 'user_agents'):
            self.user_agents = self.load_user_agents()
        if not hasattr(self, 'current_user_agent_index'):
            self.current_user_agent_index = 0
            
        if not self.user_agents:
            return None
            
        user_agent = self.user_agents[self.current_user_agent_index]
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
        return user_agent


    def setup_driver(self):
        """
        Initialize the SeleniumBase Driver with anti-detection options and user agent
        """
        user_agent = self.get_next_user_agent()

        chrome_options = {
            "uc": True,  # undetected-chromedriver mode
            "headless": False,  # false for better Cloudflare bypass
        }

        if user_agent:
            chrome_options["agent"] = user_agent
            print(f"Using User Agent: {user_agent}")

        self.driver = Driver(**chrome_options)


    def load_profile_data(self, file_path):
        """
        Load profile data from an Excel file.
        Required columns: Name, Email, Address, Password
        """
        try:
            if not (file_path.endswith('.xlsx') or file_path.endswith('.xls')):
                raise ValueError("Invalid file type. Please provide an Excel file with '.xlsx' or '.xls' extension.")
            
            data = pd.read_excel(file_path)
            required_columns = ['Name', 'Email', 'Address', 'Password']
            
            # verify all required columns exist
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
            
            return data

        except FileNotFoundError:
            raise FileNotFoundError(f"The file at {file_path} does not exist. Please check the file path.")
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"An error occurred while reading the Excel file: {str(e)}")


    def get_next_profile(self, profiles_df):
        """
        Get next profile from the dataframe in a circular manner
        """
        if self.current_profile_index >= len(profiles_df):
            self.current_profile_index = 0
        
        profile = profiles_df.iloc[self.current_profile_index]
        self.current_profile_index += 1
        return profile


    def save_cookies(self, email):
        """
        Save cookies for a profile to a JSON file
        """
        try:
            cookies = self.driver.get_cookies()
            cookie_file = os.path.join(self.cookies_dir, f"{email}.json")
            
            with open(cookie_file, 'w') as f:
                json.dump(cookies, f, indent=4)
            
            print(f"Cookies saved successfully for {email}")
            return True
        except Exception as e:
            print(f"Error saving cookies for {email}: {e}")
            return False  


    def load_profile_cookies(self, email):
        """
        Load and apply saved cookies for a profile
        """
        try:
            cookie_file = os.path.join(self.cookies_dir, f"{email}.json")
            
            if not os.path.exists(cookie_file):
                print(f"No saved cookies found for {email}")
                return False
            
            # navigate to the domain
            self.driver.get(self.website_url)
            time.sleep(2)  # wait for page to load
            
            # load and apply cookies
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
                
            for cookie in cookies:
                # remove problematic keys
                if 'expiry' in cookie:
                    del cookie['expiry']
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    print(f"Error adding cookie: {e}")
            
            # refresh page to apply cookies
            self.driver.refresh()
            time.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"Error loading cookies for {email}: {e}")
            return False  


    def verify_login_status(self):
        """
        Verify if the login was successful by checking for navbar elements
        that are only present when logged in.
        
        Returns:
            bool: True if logged in, False otherwise
        """
        try:
            # wait for either the logged-in profile section or the login button
            # to determine the current state
            WebDriverWait(self.driver, 10).until(
                lambda driver: len(driver.find_elements(By.CLASS_NAME, "sc-dWrLtm")) > 0  # profile section
                or len(driver.find_elements(By.XPATH, "//button[contains(text(), 'Login/Sign up')]")) > 0
            )
            
            # check if the profile section is present (logged in)
            profile_elements = self.driver.find_elements(By.CLASS_NAME, "sc-dWrLtm")
            if len(profile_elements) > 0:
                print("Logged in: Profile section found")
                return True
                
            # check if login button is present (not logged in)
            login_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Login/Sign up')]")
            if len(login_buttons) > 0:
                print("Not logged in: Login button found")
                return False
                
            print("Could not definitively determine login status")
            return False
            
        except TimeoutException:
            print("Timeout while checking login status")
            return False
        except Exception as e:
            print(f"Error checking login status: {e}")
            return False


    def wait_and_click(self, locator_type, locator_value, timeout=10):
        """
        Wait for element to be clickable and click it
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((locator_type, locator_value))
            )
            # random delay before clicking
            time.sleep(random.uniform(0.5, 1.5))
            element.click()
            time.sleep(random.uniform(1, 2))
            return True
        except Exception as e:
            print(f"Error clicking element: {e}")
            return False


    def wait_and_fill(self, locator_type, locator_value, text, timeout=10):
        """
        Wait for element and fill it with text
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((locator_type, locator_value))
            )
            element.clear()
            # human like typing with random delays between characters
            for char in text:
                element.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            time.sleep(random.uniform(0.5, 1))
            return True
        except Exception as e:
            print(f"Error filling element: {e}")
            return False


    def handle_cloudflare(self):
        """
        Handle Cloudflare challenge using SeleniumBase
        """
        try:
            # use SeleniumBase's built-in method to handle reconnection
            self.driver.uc_open_with_reconnect(self.website_url, reconnect_time=6)
            
            # try to click CAPTCHA if present
            try:
                self.driver.uc_gui_click_captcha()
            except:
                pass  # if no CAPTCHA, continue
                
            # additional wait to ensure page is fully loaded
            time.sleep(random.uniform(3, 5))
            return True
        except Exception as e:
            print(f"Error handling Cloudflare: {e}")
            return False


    def switch_to_english(self):
        """
        Switch website language from Greek to English
        """
        try:
            # wait and click the language switcher
            self.wait_and_click(By.XPATH, "//div[contains(text(), 'GR')]")
            time.sleep(random.uniform(0.3, 0.7))  # wait for dropdown to appear
            
            # select English option
            self.wait_and_click(By.XPATH, "//span[contains(text(), 'English (EN)')]")
            
            # wait for page to reload with new language
            time.sleep(random.uniform(2, 3))
            return True
        except Exception as e:
            print(f"Error switching language: {e}")
            return False   


    def open_registration_menu(self):
        """
        Open the registration menu
        """
        return all([
            self.wait_and_click(By.XPATH, "//button[contains(text(), 'Login/Sign up')]"),
            self.wait_and_click(By.XPATH, "//button[contains(text(), 'Login/Register with email')]"),
            self.wait_and_click(By.XPATH, "//button[contains(text(), 'Register with email')]")
        ])


    # def generate_greek_name(self):
    #     """
    #     Generate authentic Greek first and last names
    #     """
    #     # get male or female randomly
    #     if random.choice([True, False]):
    #         first_name = self.fake.first_name_male()
    #         last_name = self.fake.last_name_male()
    #     else:
    #         first_name = self.fake.first_name_female()
    #         last_name = self.fake.last_name_female()
            
    #     return first_name, last_name


    def fill_registration_form(self, profile):
        """
        Fill out the registration form
        """
        # first_name, last_name = self.generate_greek_name()
        # print(f"Creating profile with name: {first_name} {last_name}")

        name_parts = profile['Name'].split()
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:])
        email = profile['Email']

        return all([
            self.wait_and_fill(By.ID, "register_firstName", first_name),
            self.wait_and_fill(By.ID, "register_lastName", last_name),
             self.wait_and_fill(By.ID, "register_email", email),
            self.wait_and_fill(By.ID, "register_password", profile['Password']),
            self.wait_and_click(By.XPATH, "//button[@type='submit' and contains(text(), 'Continue')]")
        ])


    def navigate_and_fill_address(self, profile):
        """
        Navigate to the address input after registration, fill in the address, 
        and confirm the selection.
        """
        try:
            # navigate to the address input field
            if not self.wait_and_click(By.XPATH, "//button[contains(text(), 'Order now')]"):
                print("Failed to click the 'Order now' button.")
                return False

            # wait for the address input field to appear
            address_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Street, number, area']"))
            )

            # fill the address input field
            self.wait_and_fill(By.XPATH, "//input[@placeholder='Street, number, area']", profile['Address'])

            # wait for the dropdown to populate and click the first suggestion
            time.sleep(3)  # allow dropdown to appear

            if not self.wait_and_click(By.ID, "address-item-0"):
                print("Failed to click the first address suggestion.")
                return False

            # wait and click the Address Confirmation button
            if not self.wait_and_click(By.XPATH, "//button[contains(text(), 'Address Confirmation')]"):
                print("Failed to click the Address Confirmation button.")
                return False

            return True

        except Exception as e:
            print(f"Error in navigating and filling address: {e}")
            return False      


    def create_profile(self, profile):
        """
        Create a single profile with given email
        """
        try:
            # handle Cloudflare challenge
            if not self.handle_cloudflare():
                return False
            
            # switch to English language
            if not self.switch_to_english():
                return False
                
            # open registration menu
            if not self.open_registration_menu():
                return False
            
            # fill and submit registration form
            if not self.fill_registration_form(profile):
                return False
            
            # wait for registration to complete
            time.sleep(5)
            
            # save cookies after successful registration
            if not self.save_cookies(profile['Email']):
                print(f"Failed to save cookies for {profile['Email']}")
                return False
            
            # navigate to address input
            if not self.navigate_and_fill_address(profile):
                return False
            
            # final wait to ensure everything is processed
            time.sleep(random.uniform(3, 5))
            
            return True
            
        except Exception as e:
            print(f"Error creating profile for {profile['Email']}: {str(e)}")
            return False    


    def test_saved_profile(self, email):
        """
        Test logging in using saved cookies
        """
        try:
            self.setup_driver()
            
            if self.load_profile_cookies(email):
                if self.verify_login_status():
                    print(f"Successfully loaded profile for {email}")
                    return True
                else:
                    print(f"Cookie login failed for {email}")
            
            return False
        
        finally:
            if self.driver:
                self.driver.quit()


    # def run(self, data_file):
    #     """
    #     Main method to run the bot
    #     """
    #     try:
    #         self.setup_driver()
    #         # emails = self.load_emails(email_file)
    #         profiles_df = self.load_profile_data(data_file)
            
    #         # for email in emails:
    #         #     success = self.create_profile(email)
    #         #     if success:
    #         #         print(f"Successfully created profile for {email}")
    #         #     time.sleep(random.uniform(3, 6))

    #         for _, email_row in profiles_df.iterrows():
    #             profile = self.get_next_profile(profiles_df)
    #             success = self.create_profile(profile)

    #             if success:
    #                 print(f"Successfully created profile for {profile['Email']}")
                
    #             time.sleep(random.uniform(3, 6))
                
    #     finally:
    #         if self.driver:
    #             self.driver.quit()


    def handle_profile_creation(self):
        """
        Handle the profile creation process with browser reset between profiles
        """
        try:
            # get Excel file path
            while True:
                file_path = input("\nEnter the path to your Excel file: ").strip()
                if os.path.exists(file_path):
                    break
                print("File not found. Please try again.")

            # load profile data
            profiles_df = self.load_profile_data(file_path)
            print(f"\nFound {len(profiles_df)} profiles in Excel file.")

            # get starting row
            while True:
                try:
                    start_row = int(input(f"Enter starting row (1-{len(profiles_df)}): ").strip())
                    if 1 <= start_row <= len(profiles_df):
                        break
                    print("Invalid row number. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")

            # get number of profiles to create
            while True:
                try:
                    num_profiles = int(input(f"How many profiles to create (max {len(profiles_df)-start_row+1}): ").strip())
                    if 1 <= num_profiles <= len(profiles_df)-start_row+1:
                        break
                    print("Invalid number. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")

            # confirmation
            print("\nProfile Creation Summary:")
            print(f"Starting from row: {start_row}")
            print(f"Number of profiles to create: {num_profiles}")
            confirm = input("\nProceed? (y/n): ").strip().lower()
            
            if confirm == 'y':
                end_row = start_row + num_profiles - 1
                for index in range(start_row-1, end_row):
                    # Set up new browser instance for each profile
                    self.setup_driver()
                    try:
                        profile = profiles_df.iloc[index]
                        print(f'\nCreating profile {index+1}/{end_row} using email "{profile["Email"]}" with name "{profile["Name"]}" and address "{profile["Address"]}"')
                        success = self.create_profile(profile)
                        
                        if success:
                            print(f"Successfully created profile for {profile['Email']}")
                        else:
                            print(f"Failed to create profile for {profile['Email']}")
                        
                    finally:
                        # close the current browser instance
                        if self.driver:
                            print("Closing browser window...")
                            self.driver.quit()
                            self.driver = None
                        
                        # random delay between 2 and 3 minutes (120 to 180 seconds) before starting next profile
                        delay = random.uniform(120, 180)
                        print(f"Waiting {delay:.1f} seconds before next profile...")
                        time.sleep(delay)
                
                print("\nProfile creation process completed!")
                
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            if self.driver:
                self.driver.quit()
                self.driver = None

    def view_created_profiles(self):
        """
        Display all saved profiles from cookies directory
        """
        print("\nSaved Profiles:")
        print("-" * 50)
        
        cookie_files = os.listdir(self.cookies_dir)
        if not cookie_files:
            print("No saved profiles found.")
            return
            
        for i, file in enumerate(cookie_files, 1):
            email = file.replace('.json', '')
            print(f"{i}. {email}")
        
        print("-" * 50)


    def display_menu(self):
        """
        Display the main menu and handle user input
        """
        while True:
            print("\n" + "="*50)
            print("E-food Profile Creator - Main Menu")
            print("="*50)
            print("1. Create new profiles from Excel")
            print("2. View created profiles")
            print("3. Exit")
            print("="*50)
            
            choice = input("Enter your choice (1-3): ").strip()
            
            if choice == "1":
                self.handle_profile_creation()
            elif choice == "2":
                self.view_created_profiles()
            elif choice == "3":
                print("\nExiting program...")
                break
            else:
                print("\nInvalid choice. Please try again.")



if __name__ == "__main__":
    website_url = "https://www.e-food.gr/"
    
    print("""
    
 _____      ______              _  ______           __ _ _        _____                _              ______  _____ _____ 
|  ___|     |  ___|            | | | ___ \         / _(_) |      /  __ \              | |             | ___ \|  _  |_   _|
| |__ ______| |_ ___   ___   __| | | |_/ / __ ___ | |_ _| | ___  | /  \/_ __ ___  __ _| |_ ___  _ __  | |_/ /| | | | | |  
|  __|______|  _/ _ \ / _ \ / _` | |  __/ '__/ _ \|  _| | |/ _ \ | |   | '__/ _ \/ _` | __/ _ \| '__| | ___ \| | | | | |  
| |___      | || (_) | (_) | (_| | | |  | | | (_) | | | | |  __/ | \__/\ | |  __/ (_| | || (_) | |    | |_/ /\ \_/ / | |  
\____/      \_| \___/ \___/ \__,_| \_|  |_|  \___/|_| |_|_|\___|  \____/_|  \___|\__,_|\__\___/|_|    \____/  \___/  \_/  
                                                                                                                                                                                                                                                                                                                                                               
    """)

    bot = ProfileCreator(website_url)
    bot.display_menu()

