import setuptools

long_description = "D-Analyst is a high performance interactive visualization tool. It lets you visualize and navigate into very large plots in real time."

setuptools.setup(
    name = "D-Analyst",
    version = "1.0.0-beta",
    author = "Agbakosi Adeoluwa(180 Memes), Diachronic Technologies",
    author_email = "adeoluwaagbakosi@gmail.com",
    description = "An interactive data visualization library",
    long_description = long_description,
    url = "",
    project_urls = {
        "Bug Tracker":""
    },
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir = {"":"src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)