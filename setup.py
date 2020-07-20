import setuptools

from apptools.config import config

setuptools.setup(
    name="App tools",
    version=config.VERSION,
    description="App tools",
    author="Dexelonian",
    author_email="info@dexels.com",
    packages=setuptools.find_packages(exclude=["test"]),
    package_data={
        '': ['xcode.rb'],
    },
    install_requires=["cairosvg~=2.1.3"],
    python_requires=">=3.7",
    entry_points="""
    [console_scripts]
    app-entity=apptools.entity.cli:main
    app-strings-remove=apptools.strings.remove.cli:main
    app-strings=apptools.strings.cli:main
    app-image=apptools.image.cli:main
    """,
)
