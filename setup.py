import setuptools

long_description = "D-Analyst is a high performance interactive visualization tool. It lets you visualize and navigate into very large plots in real time."

setuptools.setup(
    name = "D-Analyst",
    version = "1.0.0-beta",
    author = "Agbakosi Adeoluwa(180 Memes), Diachronic Technologies",
    author_email = "adeoluwaagbakosi@gmail.com",
    description = "An interactive data visualization library",
    long_description = long_description,
    url = "https://github.com/Diachronic-Technologies/D-Analyst",
    project_urls = {
        "Bug Tracker":""
    },
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir = {"":"analyst"},
    packages=setuptools.find_packages(where="analyst"),
    python_requires=">=3.6",
)