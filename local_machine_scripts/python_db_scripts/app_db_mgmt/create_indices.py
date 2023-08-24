def create_indexes():
    try:
        conn = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
        cur = conn.cursor()

        cur.execute('CREATE INDEX idx_item_code_prodmerge ON prodmerge_run_data(item_code);')
        cur.execute('CREATE INDEX idx_item_code_bom ON bill_of_materials(item_code);')
        cur.execute('CREATE INDEX idx_component_description ON bill_of_materials(component_item_description);')
        cur.execute('CREATE INDEX idx_component_code ON bill_of_materials(component_item_code);')

        conn.commit()
        cur.close()
        print('Indexes created successfully.')