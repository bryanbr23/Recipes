from github import Github
from datetime import datetime, timedelta
import os
import json
import uuid
columnsToIgnore = ["Meal Planner Queue"]    # Columns to ignore in the project
project_name = "Meal Planner"
def main():
    cardsfound = False    # This is updated if columns are found and removed. Allows for message at end if still false.
    icsevents = ""
    delimcomma = ", "
    delimnewline = "\n"
    icsevent = ""
    hasrecipes = False
    project = ""
    context_dict = json.loads(os.getenv("CONTEXT_GITHUB"))
    g = Github(context_dict["token"])
    repo = context_dict["repository"]
    repo = g.get_repo(repo)
    for repoProject in repo.get_projects():
        if project_name.lower() in (repoProject.name).lower():
            project = repoProject
            print("Found project: " + project.name + " (" + str(repoProject.id) + ")")
    if project == "": print("Project " + project_name.lower() + " not found. Check project name is correct and exists in repository."); quit();
    for column in project.get_columns():
        if not column.name in columnsToIgnore:
            recipes = []
            recipesdetail = []
            hasrecipes = False
            cardsfound = True
            for card in column.get_cards():
                if card.note != None:
                    recipetitle = card.note
                    recipemore = "Note: " + card.note
                    hasrecipes = True
                    # //TODO consider flag so notes are added to event body and number of notes referenced in note title
                else:
                    issueid = (card.content_url).replace("https://api.github.com/repos/" + repo.full_name + "/issues/","")  
                    print(str(issueid))
                    issue = repo.get_issue(int(issueid))
                
                    recipetitle = issue.title + " #" + str(issue.number)
                    recipemore = issue.title + " #"  + str(issue.number) + " - " + issue.html_url
                    hasrecipes = True
                recipes.append(recipetitle)
                recipesdetail.append(recipemore)
        if hasrecipes:
            recipesjoin = list(map(str, recipes))
            if len(recipesjoin) == 1:
                icseventtitle = delimcomma.join(recipesjoin)
            if len(recipesjoin) > 1:
                icseventtitle = delimcomma.join(recipesjoin[:-1])
                icseventtitle = icseventtitle + " and " + recipesjoin[-1]
            recipesdetailjoin = list(map(str, recipesdetail))
            icseventbody = delimnewline.join(recipesdetailjoin)
            print("- " + icseventtitle)
            icstodaydate = datetime.today().strftime("%Y%m%dT%H%M%S")
            icseventdate = datetime.strptime(column.name,"%a %d-%b %Y").strftime("%Y%m%d")
            icsevent = (f"BEGIN:VEVENT\n"
            f"UID:{ uuid.uuid4() }\n"
            f"DTSTAMP:{ icstodaydate }\n"
            f"DTSTART:{ icseventdate }T184500\n"
            f"DTEND:{ icseventdate }T203000\n"
            f"SUMMARY:{ icseventtitle } for dinner\n"
            f"DESCRIPTION:{ icseventbody }\n"
            f"SEQUENCE:0\n"
            f"LOCATION:\n"
            f"TRANSP:TRANSPARENT\n"
            f"END:VEVENT\n")
            icsevents = icsevents  + icsevent
    if icsevent != "" and cardsfound:
        icsfilecontent = (f"BEGIN:VCALENDAR\n"
        f"PRODID://Bryan Bredehoeft\n"
        f"VERSION:2.0\n"
        f"X-WR-CALNAME:Meal\n"
        f"{ icsevents}"
        f"END:VCALENDAR")
#         icsFile = open('MealPlanner.ics', 'w')
#         icsFile.write(icsContent)
#         icsFile.close()
        icsfilepath = "resources/MealPlanner.ics"
        emoji = "🧑🏼‍🍳 "
        contents = ""
        
        # Post to this repo
        try:
            contents = repo.get_contents(icsfilepath, ref="main")
        except:
            print("ICS file doesn't exist doesn't exist.")
        if contents == "":
            repo.create_file(icsfilepath, emoji + "Created " + icsfilepath, icsfilecontent, branch="main")
            print(icsfilepath + " created.")
        else:
            repo.update_file(icsfilepath, emoji + "Updated " + icsfilepath, icsfilecontent, contents.sha, branch="main")
            print(icsfilepath + " updated.")           
            
if __name__ == '__main__':
    main()
