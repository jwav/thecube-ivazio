"""Defines the CubeScoresheet class, which represents a scoresheet for a cube draft.
It handles the generation of a printable scoresheet from a CubeTeamStatus instance.
"""
import asyncio
import platform
import shutil
import textwrap
import time
import weasyprint

from thecubeivazio import cube_game as cg
from thecubeivazio import cubeserver_frontdesk as cfd
from thecubeivazio.cube_common_defines import *
from thecubeivazio import cube_utils as cu
from thecubeivazio import cube_identification as cid
from thecubeivazio import cube_database as cdb
from thecubeivazio.cube_logger import CubeLogger
import pyppeteer
from pyppeteer import launch


from typing import List, Dict, Optional

SCORESHEETS_CSS_FILEPATH = os.path.join(SCORESHEETS_DIR, "scoresheet.css")

class CubeScoresheet:
    browser_names = ['brave', 'chromium', 'firefox']
    def __init__(self, team: cg.CubeTeamStatus):
        self.team = team
        self.log = CubeLogger("CubeScoresheet")

    def generate_html(self) -> str:
        team = self.team
        title = "FEUILLE DE SCORES - THE CUBE"
        creation_datetime_french = cu.timestamp_to_french_date(team.creation_timestamp)
        subtitle = f"Équipe : « {team.custom_name} » | {team.name}"

        summary_rows = ''.join([
            f'<tr><td class="col-left">Date : </td><td class="col-right">{creation_datetime_french}</td></tr>',
            f'<tr><td class="col-left">Temps alloué : </td><td class="col-right">{cu.seconds_to_hhmmss_string(team.max_time_sec,separators=["h ", "m"], secs=False)}</td></tr>',
            f'<tr><td class="col-left">Score total : </td><td class="col-right">{team.calculate_score()} points</td></tr>',
            f'<tr><td class="col-left">Cubeboxes terminées : </td><td class="col-right">{len(team.completed_cubeboxes)} ({sum(box.calculate_score() for box in team.completed_cubeboxes)} points)</td></tr>',
            f'<tr><td class="col-left">Trophées obtenus : </td><td class="col-right">{len(team.trophies_names)} ({sum(trophy.points for trophy in team.trophies)} points)</td></tr>'
        ])

        all_time_teams = cdb.find_teams_matching()
        this_years_teams = cdb.find_teams_matching(min_creation_timestamp=cu.this_year_start_timestamp())
        this_months_teams = cdb.find_teams_matching(min_creation_timestamp=cu.this_month_start_timestamp())
        this_weeks_teams = cdb.find_teams_matching(min_creation_timestamp=cu.one_week_ago_start_timestamp())
        todays_teams = cdb.find_teams_matching(min_creation_timestamp=cu.today_start_timestamp())
        # normally, a team for which a scoresheet is made is already in the database
        # but for debug purposes, we can add it to the list of teams
        for teams_list in [this_years_teams, this_months_teams, this_weeks_teams, todays_teams]:
            if not teams_list.has_team(team):
                teams_list.add_team(team)


        self.log.debug(f"all_time_teams: {len(all_time_teams)}")
        self.log.debug(f"this_years_teams: {len(this_years_teams)}")
        self.log.debug(f"this_months_teams: {len(this_months_teams)}")
        self.log.debug(f"this_weeks_teams: {len(this_weeks_teams)}")
        self.log.debug(f"todays_teams: {len(todays_teams)}")

        all_time_rank = all_time_teams.get_team_ranking_among_list(team)
        this_years_rank = this_years_teams.get_team_ranking_among_list(team)
        this_months_rank = this_months_teams.get_team_ranking_among_list(team)
        this_weeks_rank = this_weeks_teams.get_team_ranking_among_list(team)
        todays_rank = todays_teams.get_team_ranking_among_list(team)

        self.log.debug(f"all_time_rank: {all_time_rank}")
        self.log.debug(f"this_years_rank: {this_years_rank}")
        self.log.debug(f"this_months_rank: {this_months_rank}")
        self.log.debug(f"this_weeks_rank: {this_weeks_rank}")
        self.log.debug(f"todays_rank: {todays_rank}")


        ranking_rows = ''.join([
            f'<tr><td class="col-left">Classement global : </td><td class="col-right">#{all_time_rank}</td></tr>'
            f'<tr><td class="col-left">Classement pour cette année : </td><td class="col-right">#{this_years_rank}</td></tr>',
            f'<tr><td class="col-left">Classement pour ce mois : </td><td class="col-right">#{this_months_rank}</td></tr>',
            f'<tr><td class="col-left">Classement pour cette semaine : </td><td class="col-right">#{this_weeks_rank}</td></tr>',
            f'<tr><td class="col-left">Classement pour aujourd\'hui : </td><td class="col-right">#{todays_rank}</td></tr>'
        ])


        trophy_rows = ''
        for trophy in team.trophies:
            trophy_rows += f'<tr><td><img src="{trophy.image_filepath}"/></td><td>{trophy.name}</td><td>{trophy.points} points</td><td>{trophy.description}</td></tr>'


        cube_rows = ''
        for i, box in enumerate(team.completed_cubeboxes):
            box: cg.CompletedCubeboxStatus
            cube_rows += f'<tr><td>{i + 1}</td><td>{box.completion_time_str}</td><td>{box.calculate_score()}</td><td>12</td><td>6</td><td>4</td><td>2</td></tr>'

        for i in range(len(team.completed_cubeboxes) + 1, cid.NB_CUBEBOXES):
            cube_rows += f'<tr><td>{i}</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>'


        html_content = textwrap.dedent(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset='utf-8'>
                <title>{title}</title>
                <link rel='stylesheet' type='text/css' href='./scoresheet.css'>
                <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto+Slab:wght@400;700&display=swap">
            </head>
            <body>
            <div class="thecube-logo">
                <img src="../cubegui/images/logo_thecube-459x550.png" alt="The Cube Logo">
            </div>
            
            <h1>{title}</h1>
            <h2>{subtitle}</h2>
            
            <div>
                <table class="combined-summary-wrapper">
                    <tr>
                        <td>
                            <h2><img src="../cubegui/images/icon_stats.png"> Résumé</h2>
                            <div class="summary">
                                <table class="summary">
                                    {summary_rows}
                                </table>
                            </div>
                        </td>
                        <td>
                            <h2><img src="../cubegui/images/icon_ribbon.png"/> Classement</h2>
                            <div class="summary">
                                <table class="summary">
                                    {ranking_rows}
                                </table>
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
            
            <h2><img src="../cubegui/images/default_trophy_image.png"> Trophées</h2>
            <div class="score-details">
                <table>
                    <thead>
                    <tr>
                        <th></th>
                        <th>Trophée</th>
                        <th>Points</th>
                        <th>Description</th>
                    </thead>
                    {trophy_rows}
                </table>
            </div>
            
            <br/><br/>
            
            <h2><img src="../cubegui/images/icon_cube.png"> Cubes</h2>
            <div class="score-details">
                <table>
                    <thead>
                    <tr>
                        <th>Cube</th>
                        <th>Temps</th>
                        <th>Points</th>
                        <th>Classement global</th>
                        <th>Classement année</th>
                        <th>Classement mois</th>
                        <th>Classement semaine</th>
                    </tr>
                    </thead>
                    <tbody>
                    {cube_rows}
                    </tbody>
                </table>
            </div>
            </body>
            </html>
            """)
        return html_content

    @cubetry
    def save_as_html_file(self, filepath: str = None) -> bool:
        if filepath is None:
            filename = f"{self.team.name}_{int(time.time())}_scoresheet.html"
            filepath = os.path.join(SCORESHEETS_DIR, filename)
        with open(filepath, "w") as f:
            f.write(self.generate_html())
        return True

    @cubetry
    def save_as_pdf_file_with_weasyprint(self, filepath:str = None) -> bool:
        if filepath is None:
            filename = f"{self.team.name}_{int(time.time())}_scoresheet.pdf"
            filepath = os.path.join(SCORESHEETS_DIR, filename)
        html_content = self.generate_html()
        weasyprint.HTML(
            string=html_content,
            base_url=SCORESHEETS_DIR,
            encoding="utf-8"
        ).write_pdf(filepath)
        return True

    @cubetry
    def save_as_pdf_file_with_selenium(self, filepath:str = None) -> bool:
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options

        if filepath is None:
            filename = f"{self.team.name}_{int(time.time())}_scoresheet.pdf"
            filepath = os.path.join(SCORESHEETS_DIR, filename)

        self.log.info(f"Saving scoresheet as PDF: '{filepath}' ...")
        html_content = self.generate_html()
        # Write the HTML content to a temporary file
        temp_html_path = 'temp.html'
        with open(temp_html_path, 'w') as f:
            f.write(html_content)

        # Set up headless Firefox
        options = Options()

        options.headless = True

        # Start the WebDriver
        driver = webdriver.Firefox(options=options)

        # Load the HTML file
        driver.get(f"file://{temp_html_path}")

        # Give some time to ensure the page is fully loaded
        time.sleep(2)

        # Save as PDF
        with open(filepath, 'wb') as f:
            pdf = driver.execute_script('return window.print()')
            f.write(pdf)

        # Close the browser
        driver.quit()

        self.log.success(f"Scoresheet saved as PDF: {filepath}")
        return True


    @cubetry
    def save_as_pdf_file_with_pyppeteer(self, filepath: str = None, browser_choice:str=None) -> str:
        browser_choice = browser_choice or self.browser_names[0]
        if filepath is None:
            filename = f"{self.team.name}_{int(time.time())}_scoresheet.pdf"
            filepath = os.path.join(SCORESHEETS_DIR, filename)

        self.log.info(f"Saving scoresheet as PDF: '{filepath}' ...")
        html_content = self.generate_html()
        # Write the HTML content to a temporary file
        temp_html_path = os.path.join(SCORESHEETS_DIR, 'temp.html')
        with open(temp_html_path, 'w') as f:
            f.write(html_content)

        async def main():
            browser_path = self.find_browser_path(browser_choice)
            browser = await launch(executablePath=browser_path, headless=True)
            page = await browser.newPage()
            await page.goto(f"file://{temp_html_path}")

            # Wait for the font to load
            await page.evaluate("""async () => {
                await document.fonts.ready;
            }""")

            await page.pdf({'path': filepath, 'format': 'A4', 'pageRanges': '1'})
            await browser.close()

        asyncio.get_event_loop().run_until_complete(main())

        self.log.success(f"Scoresheet saved as PDF: {filepath}")
        return filepath

    def find_browser_path(self, browser_name):
        # Check if the browser is in PATH
        browser_path = shutil.which(browser_name)
        if browser_path:
            return browser_path

        # Define common installation paths
        if platform.system() == 'Windows':
            paths = {
                'firefox': [
                    r'C:\Program Files\Mozilla Firefox\firefox.exe',
                    r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe'
                ],
                'brave': [
                    r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe',
                    r'C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe'
                ],
                'chromium': [
                    r'C:\Program Files\Chromium\chromium.exe',
                    r'C:\Program Files (x86)\Chromium\chromium.exe'
                ]
            }
        elif platform.system() == 'Linux':
            paths = {
                'firefox': ['/usr/bin/firefox', '/usr/local/bin/firefox'],
                'brave': ['/usr/bin/brave-browser', '/usr/local/bin/brave-browser'],
                'chromium': ['/usr/bin/chromium-browser', '/usr/local/bin/chromium-browser']
            }
        else:
            raise ValueError(f"Unsupported operating system: {platform.system()}")

        # Check common installation paths
        for path in paths.get(browser_name, []):
            if os.path.isfile(path):
                return path

        raise FileNotFoundError(f"Could not find {browser_name} binary")



    def open_html_in_browser(self, browser_choice='firefox'):
        import webbrowser
        # Generate the HTML content
        html_content = self.generate_html()

        # Write the HTML content to a temporary file
        temp_html_path = os.path.join(SCORESHEETS_DIR, 'temp.html')
        with open(temp_html_path, 'w') as f:
            f.write(html_content)

        # Ensure the path is absolute
        absolute_html_path = 'file://' + os.path.abspath(temp_html_path)

        # Find the browser path
        browser_path = self.find_browser_path(browser_choice)

        # Register and open the browser
        webbrowser.register(browser_choice, None, webbrowser.BackgroundBrowser(browser_path))
        webbrowser.get(browser_choice).open_new_tab(absolute_html_path)



if __name__ == "__main__":
    sample_teams = cfd.generate_sample_teams()
    sample_team = sample_teams[0]
    print(f"Sample team: {sample_team}")
    scoresheet = CubeScoresheet(sample_team)
    scoresheet.log.setLevel(CubeLogger.LEVEL_DEBUG)
    scoresheet.save_as_html_file(os.path.join(SCORESHEETS_DIR, "test_scoresheet.html"))
    # scoresheet.save_as_pdf_file_with_weasyprint(os.path.join(SCORESHEETS_DIR, "test_scoresheet.pdf"))
    # scoresheet.save_as_pdf_file_with_selenium(os.path.join(SCORESHEETS_DIR, "test_scoresheet.pdf"))
    scoresheet.save_as_pdf_file_with_pyppeteer(
        os.path.join(SCORESHEETS_DIR, "test_scoresheet.pdf"),
        browser_choice="brave")
    # scoresheet.open_html_in_browser("brave")
