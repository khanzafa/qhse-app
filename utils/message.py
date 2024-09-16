# whatsapp_sender.py
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import os
import re
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import logging

class SeleniumManager:
    def __init__(self):
        self.driver = None
        self.wait = None

    def initialize_driver(self):
        # Tentukan direktori data pengguna untuk Firefox
        user_home_dir = os.path.expanduser("~")
        profile_dir = f"{user_home_dir}/.mozilla/firefox"

        # Konfigurasi opsi Firefox
        options = webdriver.FirefoxOptions()
        # Menentukan profil pengguna Firefox, jika Anda menggunakan profil khusus
        # Jika tidak menggunakan profil khusus, Anda bisa menghapus atau menyesuaikan baris ini
        options.set_preference("profile", profile_dir)
        # options.add_argument("--headless")
        self.driver = webdriver.Firefox(options=options)
        self.driver.get("https://web.whatsapp.com/")
        self.wait = WebDriverWait(self.driver, 100)

        # # Konfigurasi opsi Chrome Linux
        # user_home_dir = os.path.expanduser("~")
        # user_home_dir = user_home_dir.replace("\\", "/")

        # option = webdriver.ChromeOptions()
        # option.add_argument(f'user-data-dir={user_home_dir}/.config/google-chrome')
        # option.add_argument("--headless")
        # option.add_experimental_option("detach", True)
        # option.add_experimental_option("excludeSwitches", ["enable-automation"])
        # option.add_experimental_option('useAutomationExtension', False)
        # self.driver = webdriver.Chrome(options=option)
        # self.driver.get("https://web.whatsapp.com/")
        # self.wait = WebDriverWait(self.driver, 100)        


    def get_driver(self):
        if self.driver is None:
            self.initialize_driver()
        return self.driver

    def get_wait(self):
        if self.wait is None:
            self.initialize_driver()
        return self.wait

    def quit_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None    

selenium_manager = SeleniumManager()

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

        try:
            # Find and click the contact or group in WhatsApp
            contact_path = f'//span[contains(@title, "{target_name}")]'
            contact = wait.until(EC.presence_of_element_located((By.XPATH, contact_path)))
            contact.click()

            if image_path:
                # Click the attachment button
                attachment_box_path = '//*[@id="main"]/footer/div[1]/div/span[2]/div/div[1]/div[2]/div/div'
                attachment_box = wait.until(EC.presence_of_element_located((By.XPATH, attachment_box_path)))
                attachment_box.click()

                # Select file input and attach the image
                file_input_path = '//*[@id="main"]/footer/div[1]/div/span[2]/div/div[1]/div[2]/div/span/div/ul/div/div[2]/li/div/input'
                file_input = wait.until(EC.presence_of_element_located((By.XPATH, file_input_path)))
                file_input.send_keys(os.path.abspath(image_path))

                # Add caption
                caption_box_path = '//*[@id="app"]/div/div[2]/div[2]/div[2]/span/div/div/div/div[2]/div/div[1]/div[3]/div/div/div[2]/div[1]/div[1]'
                caption_box = wait.until(EC.presence_of_element_located((By.XPATH, caption_box_path)))

                # Send the message as a caption
                # Send the message in parts
                for part in message.split('\n\n'):  # Double newlines to split paragraphs
                    caption_box.send_keys(part)
                    caption_box.send_keys(Keys.SHIFT + Keys.ENTER)
                caption_box.send_keys(Keys.ENTER)

                # Remove image after sending
                os.remove(image_path)
            else:
                # Send the message in the text input if no image is attached
                text_box_path = '//*[@id="main"]/footer/div[1]/div[2]/div/div[2]/div[1]/div/div[2]/div/div[2]'
                text_box = wait.until(EC.presence_of_element_located((By.XPATH, text_box_path)))

                # Send the message in parts
                for part in message.split('\n\n'):  # Double newlines to split paragraphs
                    text_box.send_keys(part)
                    text_box.send_keys(Keys.SHIFT + Keys.ENTER)
                text_box.send_keys(Keys.ENTER)  
        except Exception as e:
            logging.error(f"Error while sending WhatsApp message: {e}")
            # Tambahkan penanganan kesalahan di sini jika diperlukan