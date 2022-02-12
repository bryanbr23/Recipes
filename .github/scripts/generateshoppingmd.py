
import configparser
from pathlib import Path
import os
import json
import uuid
import base64
import re
from github import Github
from pprint import pprint

# Initialize the Congig Parser.
config = configparser.ConfigParser()

ingredient_search_string = "# Ingredients"
method_search_string = "# Method"
ingredient_padding = "13"

context_dict = json.loads(os.getenv("CONTEXT_GITHUB"))
g = Github(context_dict["token"])
repo = context_dict["repository"]

# List for ingredients that are often held and don't require buying.
# //TODO consider moving this to config.ini
ingredientsHeld = ["water","seasoning","sea salt","baking soda","caster sugar","cumin","dried basil","dried oregano","garam masala","turmeric","crushed chillies","smoked paprika","garlic powder","chipotle chilli flakes","garlic cloves","sesame seeds","light brown sugar","tomato purée","tomatoes","vegetable oil","worcestershire sauce","soy sauce","light soy sauce","shichimi powder"]

ingredientsList = []                # List used for first test version. The dictionary below has replaced this.
ingredientsDict = {}                # Dictionary used to store name and value pairs (ingredient, measures)
ingredientsHeldNeededList = []      # List to capture any ingredients that are held from each recipe.
notesList = []                      # List used to store notes in from all columns.

def getIngredientByRecipeID(issue):

    # Build for single recipe
    myIssues = repo.get_issue(issue) # could filter open for e.g. repo.get_issues(state='open')

    # //TODO enhance finding the ingredient block. It pulls through 2 other list items that are at the end of my recipe #334 but not part of the ingredients block.
    issueBody = myIssues.body
    startlocation = issueBody.find(ingredient_search_string) + int(ingredient_padding)       # Note: I had to adjust to ## and 14 as this resulted in the last letter of my last ingredient being lost.
    endlocation = issueBody.find(method_search_string)   # Note: This might not always be in the issue body. Find next head after ingredients
    ingredientBlock = issueBody[startlocation:endlocation]

    # Find the list of ingredients after "# Ingredients" or "## Ingredients". Note comments above. Method isn't always available.
    # String search for # Ingredients in the myIssue.body
    # Find where # or ##
    # Recurse through each line and treat as ingredient
    # Split the measure (1 tbsp ingredient; 1 400g can ingredient; 50g ingredient) from the ingredient and subsequent application.
    # Add to dictionary ensure the ingredients remain unique but the measure reflects the measure from each recipe.

    for line in ingredientBlock.splitlines():

        ingredientMeasure = ""
        ingredientItem = line.replace("- ", "").replace("* ", "")

        # Do not append any blank lines found
        if ingredientItem != "" and ingredientItem.find("#") < 0 and ingredientItem.find("http") < 0 and ingredientItem.find("![image]") < 0 and ingredientItem.find("[") < 0:          # Note. We might need to create an exclude lines list. I don't think these are as temporary as I thought. They might always be times when there are links and images we need to remove.
            # Grab the raw ingredient before any instruction of how to use it.
            if ingredientItem.find(",") > 0:
                ingredientRaw = ingredientItem.split(",")[0]
            else:
                ingredientRaw = ingredientItem
           
            # if first is nuremic (this also catches fraction symbols from initiial testing)
            if ingredientRaw[:1].isnumeric():
                ingredientStringSplit = ingredientRaw.split(" ")

                # Remove measurement when seperated from the measure i.e. 4 tbsp.
                if ingredientStringSplit[1] == "tsp" or ingredientStringSplit[1] == "tbsp" or ingredientStringSplit[1] == "x" and ingredientStringSplit[3] != "can":
                    ingredientMeasure = ingredientStringSplit[0] + " " + ingredientStringSplit[1]
                    ingredientItem = ingredientRaw.replace(ingredientMeasure + " ","")

                # Canned ingredients are written like 1 x 400g can so these take further work to remove.
                elif ingredientRaw.find("can") > 0:
                    ingredientMeasure = ingredientStringSplit[0] + " " + ingredientStringSplit[1] + " " + ingredientStringSplit[2] + " " + ingredientStringSplit[3]
                    ingredientItem = ingredientRaw.replace(ingredientMeasure + " ","")

                    # use replace to remove the measure
                else:
                    ingredientMeasure = ingredientRaw.split(" ")[0]
                    ingredientItem = ingredientRaw.replace(ingredientMeasure,"")
                     
            else:

                # This is for when recipes donn't have a measurements like Spring onions.
                ingredientMeasure = ""
                ingredientItem = ingredientRaw 

            if ingredientMeasure != "": 
                ingredientMeasure = " " + ingredientMeasure
            else: 
                ingredientMeasure = ""

            # Add or update the item in the dictionary.
            if ingredientItem in ingredientsDict:
                ingredientsDict[ingredientItem.lower().lstrip(" ")] = ingredientsDict[ingredientItem] + " " + ingredientMeasure                       # No issue added
            else:

                # Catch singular  ingredients and replace them with their plural.
                # //TODO Consider replacing with function # https://www.codespeedy.com/program-that-pluralize-a-given-word-in-python/
                # When I looked at this I didn't think it would work - I think I read it with chilli/chillies in mind.
                ingredientItem = re.sub(r"\bonion\b","onions",ingredientItem)
                ingredientItem = re.sub(r"\bclove\b","cloves",ingredientItem)
                ingredientItem = re.sub(r"\bpepper\b","peppers",ingredientItem)
                ingredientItem = re.sub(r"\bchilli\b","chillies",ingredientItem)
                ingredientItem = re.sub(r"\banchovy\b","anchovies",ingredientItem)

                if ingredientItem.lower().lstrip(" ") in ingredientsHeld:
                    ingredientsHeldNeededList.append(ingredientItem.lower().lstrip(" "))
                else:
                    #ingredientsDict[ingredientItem.lower().lstrip(" ")] = "#" + str(issue) + ingredientMeasure + ";"
                    ingredientsDict[ingredientItem.lower().lstrip(" ")] = ingredientMeasure                      # No issue added

    return

from datetime import datetime, timedelta
import requests
import json

# //TODO move this to config.ini

apiColumnsUrl =config.get('github-credentials','apiColumnsUrl')
apiHeaders = {
    'Accept': 'application/vnd.github.inertia-preview+json',
    'Authorization': 'Bearer <snip>',
    'Content-Type': 'text/plain'
}

recipesList = []            # This list is used to store each of the recipe issues.
plannedRecipesList = []     # List to store recipes found in each column.

# Get project columns.
jsonAllProjectColumns = requests.request("GET", apiColumnsUrl, headers=apiHeaders).json()

for column in jsonAllProjectColumns:

    columnName = column["name"]
    columnRecipesList = []  # Temporary list for each of the recipes in this column.
  
    if columnName != "Meal Ideas":

        # Get the cards for this column.
        jsonCards = requests.request("GET", column["cards_url"], headers=apiHeaders).json()

        for card in jsonCards:

            if card["note"] != None:
                # Store the nores in dedicated list.
                notesList.append(columnName + ": " + card["note"])
            else:
                cardUrl = card["content_url"]
                # Add the cards issue to a list so we can retrieve the ingredients referenced in it.
                # //TODO replace this with a dynamic reference of the repo used.
                recipesList.append(int(cardUrl.replace("https://api.github.com/repos/bryanbr23/Recipes/issues/","")))

                # Get the recipe name and stored it in a list of recipes from this column.
                jsonIssue = requests.request("GET", card["content_url"], headers=apiHeaders).json()
                recipeTitle = jsonIssue["title"] + " #" + str(jsonIssue["number"])
                columnRecipesList.append(recipeTitle)

    # Add all the recipes from the column to the planned recipes list for each column pass.
    if len(columnRecipesList) > 0:
        #plannedRecipesList.append(columnName + " - " + "; ".join(list(map(str, columnRecipesList))))           # This uses an hyphen to seperate the date and the recipes.
        plannedRecipesList.append(columnName + "\n   " + "; ".join(list(map(str, columnRecipesList))))          # This uses a new line after the date and the recipes on this new line.

outputContent = (f"# Shopping List\n\nThis file has been generated to improve the sending and readability for mobile.\n\n```\nShopping List\n\n"
f"Recipes:\n\n")
print("\nSHOPPING LIST")

# Output the recipes that were used to created the ingredients list.
print("\nRecipes")

for meal in plannedRecipesList:
    print(" - " + meal + ";")

    outputContent = outputContent + (f"" + meal + "\n")

# Output the ingredients.
print("\nIngredients:")
outputContent = outputContent + (f"\nIngredients:\n\n")

# Get ingredients for each of the recipes found in the project.
for recipe in recipesList:
    getIngredientByRecipeID(recipe)

# Output each of the ingredients needed from the sort dictionary.
for key, value in sorted(ingredientsDict.items()):

    if len(value) > 0:
        measurement = " (" + value.lstrip(" ") + ")"
    
    print(" - " + key.capitalize() + measurement + "") # This outputs the ingredient, measure and a link to the grocy supplier we use. This is formatted with a new line to make it more readable as a WhatsApp message.
    content = (f"" + key.capitalize() + measurement + "\n + ")
    outputContent = outputContent + content

# Output a structured sentance of ingredients held.
delimComma = ", "
ingredientsHeld = list(map(str, sorted(set(ingredientsHeldNeededList))))

if len(ingredientsHeld) > 0:
    if len(ingredientsHeld) == 1:
        ingredientsHeldText = delimComma.join(ingredientsHeld)
    if len(ingredientsHeld) > 1:
        # Get all but the last ingredients held.
        ingredientsHeldText = delimComma.join(ingredientsHeld[:-1])
        # Join the ingredients held with the last ingredient held.
        ingredientsHeldText = ingredientsHeldText + " and " + ingredientsHeld[-1] + "."

    print("\nIngredients Held:\n" + ingredientsHeldText + "\n")          # The out put here is presented as a sentance rather than a list as it is unlikely the items referenced here are needed.
    outputContent = outputContent + (f"\nIngredients Held:\n\n" + ingredientsHeldText + "\n```")

# Write content out to file.
outputFile = open('MealPlanner\ShoppingList.md', 'w')
outputFile.write(outputContent)
outputFile.close()
