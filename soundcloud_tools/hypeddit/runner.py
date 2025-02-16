import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from soundcloud_tools.hypeddit import components as cmp
from soundcloud_tools.settings import get_settings

logger = logging.getLogger(__name__)


# Workflow Orchestrator
class WorkflowRunner:
    def __init__(self, url):
        options = webdriver.ChromeOptions()

        # path of the chrome's profile parent directory - change this path as per your system
        options.add_argument(r"--user-data-dir=")
        options.add_argument(r"--profile-directory=Profile 1")
        # options.add_argument("--no-sandbox")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # name of the directory - change this directory name as per your system
        self.driver = webdriver.Chrome(
            # service=Service(ChromeDriverManager().install()),
            options=options,
        )
        print(f"Current session is {self.driver.session_id}")
        # self.driver.get("https://www.google.com")
        # time.sleep(1000000)
        self.url = url
        # self.steps = [
        #     cmp.StartDownloadProcess(driver=self.driver),
        #     # cmp.EnterName(driver=self.driver, name=get_settings().hypeddit.name),
        #     # cmp.EnterEmail(driver=self.driver, name=get_settings().hypeddit.email),
        #     # cmp.EnterComment(driver=self.driver, name=get_settings().hypeddit.comment),
        #     # cmp.FinalDownload(self.driver),
        # ]
        self.step_mapping = {
            "sc": cmp.SoundcloudConnect,
            "yt": cmp.YoutubeConnect,
            # "1000": FinalDownloadStep  # "1000" seems to be the download step
        }
        self.steps = []

    def run(self):
        self.start()

        self.extract_steps()
        self.run_workflow()

        self.finish()

    def start(self):
        """Load the page, determine step order, and execute dynamically."""
        self.driver.get(self.url)
        time.sleep(2)  # Let the page load
        cmp.StartDownloadProcess(driver=self.driver)()
        # self.extract_steps()
        # self.run_workflow()

    def finish(self):
        """Execute the final download step."""
        cmp.FinalDownload(driver=self.driver)()
        self.driver.quit()

    def extract_steps(self):
        """Extract steps from the HTML and map them to components."""
        step_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'fangate-slider-content')]")
        logger.info(f"Found {len(step_elements)} steps.")
        logger.info(step_elements)

        for step_element in step_elements:
            try:
                step_type = step_element.get_attribute("class").split(" ")[0]
            except:
                continue
            logger.info(f"Found step type: {step_type}")
            if step_type in self.step_mapping:
                step_class = self.step_mapping[step_type](driver=self.driver)
                self.steps.append(step_class)

    def run_workflow(self):
        """Dynamically execute each step as it appears on the page."""
        for step in self.steps:
            if step.exists():
                step()
            else:
                logger.info(f"Step {step} does not exist.")

        # self.driver.quit()


if __name__ == "__main__":
    # Run the automation
    url = "https://hypeddit.com/nitodj/bound2thafunk"  # Change to your target URL
    bot = WorkflowRunner(url)
    bot.run()
