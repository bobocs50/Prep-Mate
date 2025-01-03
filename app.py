import os
import logging
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session


"""
your project’s title: Mealprep Planner
your name: Ngoc Hwang Philipp Huynh
your GitHub and edX usernames; bobocs50
your city and country; Potsdam Germany
and, the date you have recorded this video: 6.10.2024
"""





#Configure application
app = Flask(__name__)

#SQLite database
db = SQL("sqlite:///data.db")




@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        def insert_meal(meal_name, servings, notes, ingredients, quantities, units):
            #insert meal and serving 
            db.execute("INSERT INTO meals (meal_name, servings) VALUES(?, ?)",
                    meal_name.lower(), int(servings))

            #fetch meal_id
            meal_id = db.execute("SELECT last_insert_rowid() AS id")[0]["id"]

            #insert notes with meal_id
            db.execute("INSERT INTO notes (meal_id, note_text) VALUES(?,?)", 
                        meal_id, notes)

            #insert ingredients with meal_id
            for i in range(len(ingredients)):
                db.execute("INSERT INTO ingredients (meal_id, ingredient_name, quantity, unit) VALUES(?, ?, ?, ?)",
                        meal_id, ingredients[i].lower(), float(quantities[i]), units[i].lower())

        #get meal input
        meal_name = request.form.get("meal_name")
        servings = request.form.get("servings")
        notes = request.form.get("notes")

        ingredients = request.form.getlist('ingredients[]')
        quantities = request.form.getlist('quantities[]')
        units = request.form.getlist('units[]')

        #call insert function
        insert_meal(meal_name, servings, notes, ingredients, quantities, units)
    
        return redirect("/")


    return render_template("index.html")



@app.route("/select", methods=["GET", "POST"])
def select():

    if request.method == "GET":

        def meal_table():
            #list to store meals
            meals_list = []
            #get meals for table
            meals_data = db.execute("SELECT meal_name, servings FROM meals")
            #put meals into meals_list
            for item in meals_data:
                    meals_list.append({
                        "meal_name": item["meal_name"].title(),
                        "servings": item["servings"]
                        })
            
            return meals_list


        def recipe_table():
            #fetch meals for recipe_tables
            meals = db.execute("SELECT meal_id, meal_name, servings FROM meals_new")

            #dict to store recipe
            recipe_data = {}

            for meal in meals:
                #get id from meals_new
                meal_id = meal['meal_id']

                # fetch ingredients with id
                ingredients = db.execute("SELECT ingredient_name, quantity, unit FROM ingredients_new WHERE meal_id = ?", meal_id)
                # fetch notes with id
                notes = db.execute("SELECT note_text FROM notes WHERE meal_id = ?", meal_id)
                
                #store into recipe_data
                recipe_data[meal['meal_name']] = {
                    'servings': meal['servings'],
                    'ingredients': ingredients,
                    'notes': notes
                }
          
            return recipe_data




        #Main flow
        meals_list = meal_table()
        recipe_data = recipe_table()


        return render_template("select.html", meals=meals_list, recipe_data=recipe_data)




    elif request.method == "POST":

        
        def delete_from_table():
            delete_meals = request.form.getlist("delete_meals")
            delete_meals =  [meal.lower() for meal in delete_meals]

            for meal1 in delete_meals:
                id_delete = db.execute("SELECT id FROM meals WHERE meal_name = ?", meal1) [0]["id"]
                print(id_delete)
                
                #Delete meal from everywhere
                db.execute("DELETE FROM ingredients WHERE meal_id = ?", id_delete)
                db.execute("DELETE FROM ingredients_new WHERE meal_id = ?", id_delete)
                db.execute("DELETE FROM notes WHERE meal_id = ?", id_delete)
                db.execute("DELETE FROM meals_new WHERE meal_id = ?", id_delete)
                db.execute("DELETE FROM meals WHERE id = ?", id_delete)

        def filter_serving(selected_servings):
            #filter out whitespace from list and append to list
            filtered_serving = []

            for serving in selected_servings:
                if serving.strip():
                    filtered_serving.append(int(serving))
            
            return filtered_serving

        def calculate_insert_ingredient(selected_meals, filtered_servings):

            #scale the meals

            current_meal = 0

            for meal in selected_meals:

                #fetch meal id
                id = db.execute("SELECT id FROM meals WHERE meal_name = ?", meal.lower())[0]["id"]

                #get the quantities of ingredient with meal_id
                quantities_dict= db.execute("SELECT quantity FROM ingredients WHERE meal_id = ?", id)

                #extract quantity of ingredient dict into a list
                quantities = [ingredient["quantity"] for ingredient in quantities_dict]

                print(quantities)
                print("TESTTTTT")
            
                #interate through each quantitiy of ingredient and multiply with serving
                updated_quantities = []

                for quantity in quantities:
                    new_quantity = quantity * filtered_serving[current_meal]
                    updated_quantities.append(new_quantity)
                
                print(updated_quantities)



                #INSERTING INTO RECIPES




                #insert meals into meals_new table
                db.execute("INSERT INTO meals_new (meal_name, servings, meal_id) VALUES(?, ?, ?)",
                        selected_meals[current_meal].lower(), filtered_serving[current_meal], id)

                #fetch ingredients and unit from ingredients
                ingredients = db.execute("SELECT ingredient_name FROM ingredients WHERE meal_id = ?", id)
                units = db.execute("SELECT unit FROM ingredients WHERE meal_id = ?", id)

                #extract ingredients and unit and put them into a list
                updated_ingredients = [ingredient["ingredient_name"].lower() for ingredient in ingredients]
                updated_units = [unit["unit"] for unit in units]
        
                #insert ingredients, quantity and unit into ingredients_new
                for i in range(len(ingredients)):
                    db.execute("INSERT INTO ingredients_new (meal_id, ingredient_name, quantity, unit) VALUES(?, ?, ?, ?)",
                            id, updated_ingredients[i].lower(), round(updated_quantities[i], 2), updated_units[i].lower())





                #PUT INGREDIENTS, QUANTITY AND UNIT INTO GROCERY LIST




                grocery_list = db.execute("SELECT ingredient_name, quantity FROM grocery_list")

                #lists
                existing_ingredients = []
                existing_quantities = []

                #add into list
                for i in grocery_list:
                    existing_ingredients.append(i["ingredient_name"].lower())
                    existing_quantities.append(i["quantity"])


                #iterate trough each ingredient
                for i, ingredient in enumerate(updated_ingredients):

                    if ingredient in existing_ingredients:
                        #find index of the ingredient
                        index = existing_ingredients.index(ingredient)
                        #add up quantities
                        new_quantity = existing_quantities[index] + updated_quantities[i]
                        #update database
                        db.execute("UPDATE grocery_list SET quantity = ? WHERE ingredient_name = ?",
                        new_quantity, ingredient)

                    else:
                        db.execute("INSERT INTO grocery_list (ingredient_name, quantity, unit) VALUES(?,?,?)",
                            ingredient.lower(), updated_quantities[i], updated_units[i].lower())



                #increment to move to next meal
                current_meal += 1






        #main flow

        #delete from table function
        delete_from_table()

        #get input from cook and serving
        selected_meals = request.form.getlist("selected_meals")
        selected_servings = request.form.getlist("selected_servings")
        
        #filter whitespace from servings
        filtered_serving = filter_serving(selected_servings)

        #calculate and insert ingredient
        calculate_insert_ingredient(selected_meals, filtered_serving)

        return redirect("select")



@app.route("/list", methods=["GET","POST"])
def list():
    if request.method == "POST":

        def reset_list():
            #delete Grovery list
            db.execute("DELETE FROM grocery_list")
            #delete the submited meals from SELECT
            db.execute("DELETE FROM ingredients_new")
            db.execute("DELETE FROM meals_new")



        #main flow
        reset_list()

        return redirect("/select")


    elif request.method =="GET":

        #fetch grovery_list
        grocery_list = db.execute("SELECT ingredient_name, quantity, unit FROM grocery_list")

        return render_template("list.html", grocery_list=grocery_list)



if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)
