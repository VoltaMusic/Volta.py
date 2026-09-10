from setuptools import setup, find_packages

setup(
	name="VoltaLib",
	version="0.7.3",
	description="VoltaLibPython packaged as VoltaLib",
	packages=find_packages(exclude=("tests", "docs")),
	include_package_data=True,
	install_requires=["dotenv", "requests"],
	python_requires=">=3.8",
	author="Zerbaib",
	license="",
)
