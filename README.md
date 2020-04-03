# HermesRCSS

HermesRCSS is a notification bot intended to message you via the [Webex Teams](https://teams.webex.com) messaging client.

## Installation for developers

1. Clone this repository.

```bash
git clone https://jxoesneon@bitbucket.org/joseeroj/hermesbot.git
```
2. Install pipenv to handle enviroment and requirements
```bash
pip install pipenv
```
3. Install all the requirements (include --dev to install development requirements)
```bash
pipenv install --dev
```
4. start the virtual enviroment
```bash
pipenv shell
```
## Usage for users

- Log in to Webex Teams 
    - Via web at https://teams.webex.com
    - Via the app https://www.webex.com/downloads.html
- Search for the bot on the search bar
    - By name:
    - ![searchbyname.png](media/searchbyname.png)
    - By url:
    - ![searchbyurl.png](media/searchbyurl.png)
- Click on the bot to start a space with it.
- Send the command "/subscribe" to get added to the list.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[GNU GPLv3](https://choosealicense.com/licenses/gpl-3.0/)