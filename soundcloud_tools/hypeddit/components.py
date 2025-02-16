import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class BaseComponent(BaseModel, ABC):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    driver: WebDriver
    element: WebElement | None = None

    # def __init__(self, driver):
    #     self.driver = driver
    #     self.position = None  # Store position of element on the page

    def __call__(self):
        self.exists()
        if self.element:
            self.run()
        else:
            raise ValueError(f"Element {self.__class__.__name__} not found")

    @abstractmethod
    def run(self):
        """Each step must implement this."""
        raise NotImplementedError("Subclasses must implement run()")

    @abstractmethod
    def exists(self):
        """Each step must implement how it checks for existence."""
        raise NotImplementedError("Subclasses must implement exists()")

    def find_element(self, value, by: By = By.XPATH):
        """Get element position (if exists)."""
        # try:
        return self.driver.find_element(by=by, value=value)
        # except Exception as e:
        #     logger.error(e)
        #     return None


class StartDownloadProcess(BaseComponent):
    def run(self):
        logger.info("Starting Download process...")

        with open("cookies3.yaml") as f:
            import yaml

            cookies = yaml.safe_load(f)

        # Add each cookie to the driver
        for name, value in cookies.items():
            ck = {"name": name, "value": value}
            logger.info(f"Adding cookie: {ck}")
            self.driver.add_cookie(ck)

        self.driver.refresh()
        self.exists()
        if self.element:
            self.element.click()
            time.sleep(0.5)

    def exists(self):
        self.element = self.find_element("downloadProcess", by=By.ID)
        return self.element is not None


class SoundcloudConnect(BaseComponent):
    def run(self):
        logger.info("Connecting with SoundCloud...")

        # with open("cookies3.yaml") as f:
        #     import yaml

        #     cookies = yaml.safe_load(f)

        # # Add each cookie to the driver
        # for name, value in cookies.items():
        #     ck = {"name": name, "value": value}
        #     logger.info(f"Adding cookie: {ck}")
        #     self.driver.add_cookie(ck)

        # self.driver.refresh()
        # time.sleep(2)

        self.element.click()
        # A new tab opens which we have to click a button in
        time.sleep(2)
        self.driver.switch_to.window(self.driver.window_handles[1])

        time.sleep(4)

        # sc = self.driver.get_screenshot_as_png()
        # with open("sc.png", "wb") as f:
        #     f.write(sc)
        # self.driver.find_element(By.XPATH, "//button[contains(@class, 'google-plus-signin')]").click()
        # time.sleep(2)
        # # Switch to new tab
        # self.driver.switch_to.window(self.driver.window_handles[2])
        # time.sleep(0.5)
        # self.driver.switch_to.window(self.driver.window_handles[1])
        # time.sleep(0.5)
        self.driver.find_element(By.ID, "submit_approval").click()
        time.sleep(2)
        self.driver.switch_to.window(self.driver.window_handles[0])

    def exists(self):
        self.element = self.find_element("login_to_sc", by=By.ID)
        return self.element is not None


class YoutubeConnect(BaseComponent):
    # Example HTML:
    # <a class="button button-highlight undone" href="javascript:void(0);" alt="Subscribe on YouTube" onclick="PopupCenterDual('https://www.youtube.com/@SINDEX.techno?sub_confirmation=1','yt_popup','500','500');$(this).removeClass('undone');" style="text-align:left; padding: 0 10px; text-overflow: ellipsis; overflow: hidden;" data-url="https://www.youtube.com/@SINDEX.techno?sub_confirmation=1" data-title="SINDEX"><i class="fa fa-youtube" style="font-size:20px; margin-left:0;"></i> Subscribe To <span style="font-family: 'hypefontregular';">SINDEX</span></a>
    def run(self):
        logger.info("Connecting with Youtube...")
        self.element.click()
        # A new tab opens which we have to click a button in
        time.sleep(2)

    def exists(self):
        self.element = self.find_element("login_to_yt", by=By.ID)
        return self.element is not None


class EnterName(BaseComponent):
    name: str

    def run(self):
        logger.info("Entering name...")
        self.element.send_keys(self.name)
        self.element.send_keys(Keys.RETURN)
        time.sleep(2)

    def exists(self) -> bool:
        self.element = self.find_element("//input[@name='name']")
        return bool(self.element)


class EnterEmail(BaseComponent):
    email: str

    def run(self):
        logger.info("Entering email...")
        input_box = self.driver.find_element(By.XPATH, "//input[@name='email']")
        input_box.send_keys(self.email)
        input_box.send_keys(Keys.RETURN)
        time.sleep(2)

    def exists(self):
        self.position = self.element_position("//input[@name='name']")
        return self.position is not None


class EnterComment(BaseComponent):
    comment: str

    def run(self):
        logger.info("Entering comment...")
        comment_box = self.driver.find_element(By.XPATH, "//textarea[@name='comment']")
        comment_box.send_keys(self.comment)
        comment_box.send_keys(Keys.RETURN)
        time.sleep(2)

    def exists(self):
        self.position = self.element_position("//textarea[@name='comment']")
        return self.position is not None


class FinalDownload(BaseComponent):
    def run(self):
        logger.info("Clicking download button...")
        self.element.click()
        self.driver.execute_script("arguments[0].click();", self.element)
        logger.info("Download started!")
        time.sleep(1)

    def exists(self):
        self.element = self.find_element("gateDownloadButton", by=By.ID)
        return self.element is not None  # Always required
