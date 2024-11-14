def page_has_category(page, category_name):
    for category in page.categories():
        if category.name == category_name:
            return True

    return False
