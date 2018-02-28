from setuptools import setup, find_packages

setup(
    name='telegram-logging-bot',
    version='v0.1',
    packages=find_packages(),
    url='https://github.com/bogdandm/telegram-logging-bot',
    license='MIT',
    author='Bogdan Kalashnikov',
    author_email='bogdan.dm1995@yandex.ru',
    description='Bot to auto notify server errors and store them for future analyze',
    install_requires=list(map(str.strip, open("requirements.txt", "r").readlines()))
)
