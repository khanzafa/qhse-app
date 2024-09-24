# whatsapp_sender.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import os
import re
import logging

class SeleniumManager:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.actions = None

    def initialize_driver(self):
        # Tentukan direktori profil Firefox
        profile_path = '/home/khanza/.mozilla/firefox/vivmnzdj.khanza'  # Ganti dengan path profil yang sesuai

        # Buat opsi Firefox dan profil
        firefox_options = Options()
        firefox_profile = FirefoxProfile(
            profile_directory=profile_path
        )
        # firefox_options.add_argument('--headless')
        # firefox_profile.set_preference("javascript.enabled", False)
        firefox_options.profile = firefox_profile
        self.driver = webdriver.Firefox(options=firefox_options)
        self.driver.get("https://web.whatsapp.com/")
        self.wait = WebDriverWait(self.driver, 150)
        self.actions = ActionChains(self.driver)

        # Konfigurasi opsi Chrome Linux
        # option = webdriver.ChromeOptions()  
        # self.driver = webdriver.Chrome(options=option)
        # self.driver.get("https://web.whatsapp.com/")
        # self.wait = WebDriverWait(self.driver, 100)        
        # self.actions = ActionChains(self.driver)

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
            contact_path = f'//span[contains(@title, "{target_name}")]'
            contact = wait.until(EC.presence_of_element_located((By.XPATH, contact_path)))
            contact.click()

            text_box_xpath = '/html/body/div[1]/div/div/div[2]/div[4]/div/footer/div[1]/div/span[2]/div/div[2]/div[1]/div/div[1]/p'
            text_box = wait.until(EC.presence_of_element_located((By.XPATH, text_box_xpath)))

            actions.move_to_element(text_box).click().send_keys(message).perform()

            if image_path:
                attachment_button_xpath = '/html/body/div[1]/div/div/div[2]/div[4]/div/footer/div[1]/div/span[2]/div/div[1]/div[2]/div/div'
                attachment_button = wait.until(EC.presence_of_element_located((By.XPATH, attachment_button_xpath)))

                attachment_button.click()

                image_button_xpath = '/html/body/div[1]/div/div/div[2]/div[4]/div/footer/div[1]/div/span[2]/div/div[1]/div[2]/div/span/div/ul/div/div[2]/li/div/input'
                image_button = wait.until(EC.presence_of_element_located((By.XPATH, image_button_xpath)))

                image_button.send_keys(image_path)

                send_button_xpath = '/html/body/div[1]/div/div/div[2]/div[2]/div[2]/span/div/div/div/div[2]/div/div[2]/div[2]/div/div'
                send_button = wait.until(EC.presence_of_element_located((By.XPATH, send_button_xpath)))

                send_button.click()
                actions.move_to_element(text_box).send_keys(Keys.ESCAPE).send_keys(Keys.ESCAPE).send_keys(Keys.ESCAPE).perform()
            else:
                actions.move_to_element(text_box).send_keys(Keys.RETURN).perform()
                actions.move_to_element(text_box).send_keys(Keys.ESCAPE).send_keys(Keys.ESCAPE).send_keys(Keys.ESCAPE).perform()
                
        except Exception as e:
            logging.error(f"Error while sending WhatsApp message: {e}")
            # Tambahkan penanganan kesalahan di sini jika diperlukan