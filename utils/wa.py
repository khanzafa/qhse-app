# whatsapp_sender.py
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import os

def send_whatsapp_message(app, target_name, message, image_path):
    """
    Sends a message and an image to a specified WhatsApp contact using Selenium.

    Parameters:
    - app: Flask app object containing the WebDriver instance.
    - target_name: Name of the contact or group in WhatsApp.
    - message: Message to be sent.
    - image_path: Path of the image to be attached (optional).
    """
    driver = app.driver
    wait = app.wait

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
            for part in message.split('||'):
                caption_box.send_keys(part)
                caption_box.send_keys(Keys.SHIFT + Keys.ENTER)
            caption_box.send_keys(Keys.ENTER)

            # Remove image after sending
            os.remove(image_path)
        else:
            # Send the message in the text input if no image is attached
            text_box_path = '//*[@id="main"]/footer/div[1]/div[2]/div/div[2]/div[1]/div/div[2]/div/div[2]'
            text_box = wait.until(EC.presence_of_element_located((By.XPATH, text_box_path)))

            for part in message.split('||'):
                text_box.send_keys(part)
                text_box.send_keys(Keys.SHIFT + Keys.ENTER)
            text_box.send_keys(Keys.ENTER)
    except Exception as e:
        print(f"Error while sending WhatsApp message: {e}")
