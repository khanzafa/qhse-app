# whatsapp_sender.py
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.firefox.options import Options
# from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import os
import re
import logging
from colorama import Back, Style
import flask_mail

class SeleniumManager:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.actions = None

    def initialize_driver(self):
        # Firefox Linux
        # profile_path = '/home/khanza/.mozilla/firefox/vivmnzdj.khanza'  # Ganti dengan path profil yang sesuai
        # firefox_options = Options()
        # firefox_profile = FirefoxProfile(
        #     profile_directory=profile_path
        # )
        # firefox_options.add_argument('--headless')
        # firefox_profile.set_preference("javascript.enabled", False)
        # firefox_options.profile = firefox_profile
        # self.driver = webdriver.Firefox(options=firefox_options)
        # self.driver.get("https://web.whatsapp.com/")
        # self.wait = WebDriverWait(self.driver, 150)
        # self.actions = ActionChains(self.driver)

        # Chrome Linux
        # option = webdriver.ChromeOptions()  
        # self.driver = webdriver.Chrome(options=option)
        # self.driver.get("https://web.whatsapp.com/")
        # self.wait = WebDriverWait(self.driver, 100)        
        # self.actions = ActionChains(self.driver)
        
        # Chrome Windows
        chrome_options = Options()
        # chrome_options.add_argument("--user-data-dir=C:\\Users\\hp\\AppData\\Local\\Google\\Chrome\\User Data")
        # chrome_options.add_argument("--profile-directory=Default")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get("https://web.whatsapp.com/")
        self.wait = WebDriverWait(self.driver, 100)
        self.actions = ActionChains(self.driver)

        logging.info('Selenium driver initialized')
        
        print(Back.BLUE+"Selenium driver initialized")        
        print(Style.RESET_ALL)
        mail_manager.refresh_and_send()
        print(Back.RED)
        logging.info('sdh selesai scan')
        print(Style.RESET_ALL)

    def get_driver(self):
        if self.driver is None:
            self.initialize_driver()
        return self.driver

    def get_wait(self):
        if self.wait is None:
            self.initialize_driver()
        return self.wait
    
    def get_actions(self):
        if self.actions is None:
            self.initialize_driver()
        return self.actions

    def quit_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None  
            self.actions = None  

selenium_manager = SeleniumManager()

class MailManager():
    def __init__(self):
        self.barcode_path = '//canvas[@aria-label="Scan this QR code to link a device!"]'
        self.previous_data_ref = None
        
    def init_app(self, app):
        self.app = app
        print(Back.MAGENTA)
        print("Mail Manager initialized.")
        print(Style.RESET_ALL)
        print(f"self app: {self.app}")
        print(f"app: {app}")
        
    def send_barcode(self):
        try:
            barcode = selenium_manager.wait.until(EC.presence_of_element_located((By.XPATH, self.barcode_path)))  # Update this line
            barcode_img = barcode.screenshot_as_png
            with open('barcode.png', 'wb') as f:
                f.write(barcode_img)
            
            # Send the barcode image via email
            subject = "Your Whatsapp Barcode"
            recipient = 'aihseintern@gmail.com'  # Get recipient email from environment variable
            body = "Please find the attached barcode image."
            
            with open('barcode.png', 'rb') as f:
                msg = flask_mail.Message(subject, sender=os.getenv('MAIL_USERNAME'), recipients=[recipient])
                msg.body = body
                msg.attach('barcode.png', 'image/png', f.read())
            
            with self.app.app_context():
                from app import mail
                mail.send(msg)
            
            print(Back.GREEN)
            print("Barcode sent successfully!")
            print(Style.RESET_ALL)
            return "Barcode sent successfully!"
        
        except Exception as e:
            return "Failed to send barcode."

    def refresh_and_send(self):
        last_refresh = time.time()
        
        print("last_refresh: ", last_refresh)
        
        while True:
            if time.time() - last_refresh > 50:
                selenium_manager.driver.refresh()
                last_refresh = time.time()
            time.sleep(1)
            try:
                barcode_element = selenium_manager.driver.find_element("xpath", '//div[@class="_akau"]')
                current_data_ref = barcode_element.get_attribute("data-ref")
                if current_data_ref != self.previous_data_ref:
                    self.send_barcode()
                    self.previous_data_ref = current_data_ref
            except Exception as e:
                self.previous_data_ref = None
                print(Back.RED)
                logging.info(f"Barcode scanned successfully, element not found", {e})
                print(Style.RESET_ALL)
                return
            
mail_manager = MailManager()

class Message:
    def __init__(self, message_template, detected_object):
        self.message_template = message_template
        self.detected_object = detected_object

    def render(self):
        # Replace placeholders in the template with actual data from detected_object
        rendered_message = self.message_template
        
        for key, value in self.detected_object.items():
            placeholder = "@" + key
            # print("Placeholder: ", placeholder)
            rendered_message = rendered_message.replace(placeholder, str(value))

        # Remove any remaining placeholders that were not replaced
        rendered_message = re.sub(r'\{\{.*?\}\}', '', rendered_message)
        
        return rendered_message
    
    @staticmethod
    def send_whatsapp_message(target_name, message, image_path):
        driver = selenium_manager.get_driver()
        wait = selenium_manager.get_wait()
        actions = selenium_manager.get_actions()

        try:
            # contact_path = f'//span[contains(@title, "eh")]'
            contact_path = f'//span[@title="{target_name}"]'       
            contact = wait.until(EC.presence_of_element_located((By.XPATH, contact_path)))
            contact.click()

            text_box_xpath = '/html/body/div[1]/div/div/div[2]/div[4]/div/footer/div[1]/div/span/div/div[2]/div[1]/div/div[1]/p'
            text_box = wait.until(EC.presence_of_element_located((By.XPATH, text_box_xpath)))
            
            # Loop through the message but send it all at once
            actions.move_to_element(text_box).click().send_keys(message).perform()

            if image_path:
                attachment_button_xpath = '/html/body/div[1]/div/div/div[2]/div[4]/div/footer/div[1]/div/span/div/div[1]/div[2]/div/div/div/span'
                attachment_button = wait.until(EC.presence_of_element_located((By.XPATH, attachment_button_xpath)))

                attachment_button.click()
                
                image_button_xpath = '/html/body/div[1]/div/div/div[2]/div[4]/div/footer/div[1]/div/span/div/div[1]/div[2]/div/span/div/ul/div/div[2]/li/div/input'
                image_button = wait.until(EC.presence_of_element_located((By.XPATH, image_button_xpath)))

                image_button.send_keys(image_path)
                
                # /html/body/div[1]/div/div/div[2]/div[4]/div/footer/div[1]/div/span/div/div[2]/div[2]

                send_button_xpath = '/html/body/div[1]/div/div/div[2]/div[2]/div[2]/span/div/div/div/div[2]/div/div[2]/div[2]/div/div'
                send_button = wait.until(EC.presence_of_element_located((By.XPATH, send_button_xpath)))

                send_button.click()
                # actions.move_to_element(text_box).send_keys(Keys.ESCAPE).send_keys(Keys.ESCAPE).send_keys(Keys.ESCAPE).perform()
            else:
                actions.move_to_element(text_box).send_keys(Keys.RETURN).perform()
                actions.move_to_element(text_box).send_keys(Keys.ESCAPE).send_keys(Keys.ESCAPE).send_keys(Keys.ESCAPE).perform()
                
        except Exception as e:
            logging.error(f"Error while sending WhatsApp message: {e}")
            # Tambahkan penanganan kesalahan di sini jika diperlukan