import pyodbc
from pyodbc import Error
import psycopg2
import os
from dotenv import load_dotenv

def check_all_filenames():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(current_dir, '..', '..', '.env')
    load_dotenv(dotenv_path=env_path)

    SAGE_USER = os.getenv('SAGE_USER')
    SAGE_PW = os.getenv('SAGE_PW')

    if not SAGE_USER or not SAGE_PW:
        raise ValueError("Sage credentials not found in environment variables.")
    connection_postgres = psycopg2.connect('postgresql://postgres:blend2021@localhost:5432/blendversedb')
    cursor_postgres = connection_postgres.cursor()
    cursor_postgres.execute("""SELECT itemcode FROM CI_Item 
        WHERE itemcodedesc LIKE 'BLEND%';
    """)
    blend_items = cursor_postgres.fetchall()
    blend_items_list = []
    for item in blend_items:
        item_code = item[0].strip()
        if item_code not in blend_items_list:
            blend_items_list.append(item_code)

    connection_postgres.commit()
    cursor_postgres.close()
    connection_postgres.close()

    filenames = [
        '031018  DNA.docx',
        '052000G2-2-15 KPK Tote Warning 07-14-2022.docx',
        '052000G8-16 -50 Antifreeze KPK Tote Warning 04-21-2022.docx',
        '052002 PG 80 KPK Tote Warning 11-02-23.docx',
        '052003G39-51GRN -200 KPK Tote Warning 04-20-2022.docx',
        '052004N Biosafe Antifreeze KPK Tote Warning 04-20-2022.docx',
        '052004PURPLE Biosafe Antifreeze Coolant KPK Tote Warning 04-21-2022.docx',
        '089300.B Gel Teak Cleaner KPK Tote Warning 04-20-2022.docx',
        '100501K TCW3 KPK Tote Warning 04-18-2022.docx',
        '101762 Liquid Rubbing Compound KPK Tote Warning 04-20-2022.docx',
        '101766 Premium Marine Polish KPK Tote Warning 04-20-2022.docx',
        '101781 Heavy Duty Cleaner Wax KPK Tote Warning 04-20-2022.docx',
        '112000.B Purple Clnr Degr KPK Tote Warning 08-17-202.docx',
        '113000.B Orange Clnr Degr KPK Tote Warning 07-30-2024.docx',
        '1170570.B Nit Nut KPK Tote Warning 1-7-20.docx',
        '118000.B Pine Multipurpose Clnr KPK Tote Warning 08-13-2024.docx',
        '124971 Restorer Wax KPK Tote Warning 04-19-2022.docx',
        '14308.B Startron Auto Gas KPK Tote Warning 04-18-2022.docx',
        '14308AMBER.B Startron Amber Auto Gas KPK Tote Warning 04-20-2022.docx',
        '14800.B Startron Stabilizer KPK Tote Warning 06-1-2022.docx',
        '16600.B Break In Oil KPK Tote Warning 04-18-2023.docx',
        '18500.B Hydraulic Fluid KPK Tote Warning 04-18-2022.docx',
        '19901B Snappy Teak Nu Caustic KPK Tote Warning 1-7-20.docx',
        '19902.B Snappy Teak Nu Acid  Tote Warning 12-19-19.docx',
        '19903B Snappy Teak Nu Caustic KPK Tote Warning 1-7-20.docx',
        '203300.B Ceramic Metal Protectant KPK Tote Warning 12-04-2023.docx',
        '203500.B  Ceramic Wash & Wax Tote Warning 02-9-24.docx',
        '203700.B Speed Detailer KPK Tote Warning 12-04-2023.docx',
        '203900.B Ceramic Vinyl KPK Tote Warning 12-04-2023.docx',
        '27200.B 80W90 KPK Tote Warning 04-18-2022.docx',
        '27300.B Type C Gear Lube  KPK Tote Warning 04-18-2022.docx',
        '27800.B Engine Oil 30W KPK Tote Warning 04-18-2022.docx',
        '27900.B Engine Oil 40W KPK Tote Warning 06-21-2022.docx',
        '28000.B  Engine Oil 15W40 KPK Tote Warning 04-18-2022.docx',
        '28100.B 10W30 KPK Tote Warning 04-18-2022.docx',
        '28200.B  Engine Oil 10W40 KPK Tote Warning 04-18-2022.docx',
        '28300.B  Engine Oil 25W40 KPK Tote Warning 04-18-2022.docx',
        '28500.B Trim Tilt 04-28-2022.docx',
        '300355.B ITW LC KPK Tote Warning 04-20-2022.docx',
        '300357.B ITW Aluminum Coolant KPK Tote Warning 04-20-2022.docx',
        '315xx KPK Tote Warning 10-29-2024.docx',
        '32500.B Organic AF KPK Tote Warning 06-28-2023.docx',
        '32700.B Boiler Antifreeze -100 KPK Tote Warning 04-21-2022.docx',
        '33200CONC.B Full Strength Liquid Chill Coolant KPK Tote Warning 04-21-2022.docx',
        '33200DIL.B StarCool Coolant KPK Tote Warning 04-21-2022.docx',
        '33400.B Tropical AF KPK Tote Warning 04-21-2022.docx',
        '33500.B Full Strength 750,000 Mile KPK Tote Warning 04-21-2022.docx',
        '33600.B 750,000 Mile KPK Tote Warning 04-21-2022.docx',
        '33700.B Instrument AF 50-50 KPK Tote Warning 07-10-2023.docx',
        '33900.B Recharge Fluid  Tote Warning 10-25-22.docx',
        '44200.B UV Protectant KPK Tote Warning 04-20-2022.docx',
        '500200 Methanol.docx',
        '500400 Extreme Clean Windshield Washer Fluid  KPK Tote Warning 04-21-2022.docx',
        '500500 -10 F Windshield Washer Fluid  KPK Tote Warning 04-21-2022.docx',
        '500501 +21F Windshield Washer Fluid  KPK Tote Warning 04-21-2022.docx',
        '5359351.B  HeadChem Mint KPK Tote Warning 04-18-2022.docx',
        '54900.B Gel Pool Calcium Remover KPK Tote Warning 04-20-2022.docx',
        '55432.B Composite Deck Cleaner KPK Tote Warning 04-20-2022.docx',
        '57000.B Gel Deck Cleaner KPK Tote Warning 08-23-2022.docx',
        '57400.B Gel Teak Cleaner Brightener KPK Tote Warning 1-21-20.docx',
        '57700B BBQ Cleaner KPK Tote Warning 1-7-20.docx',
        '58200.B Composite Deck Protector KPK Tote Warning 08-08-2022.docx',
        '601009 50-50 Pre Diluted AF KPK Tote Warning 04-21-2022.docx',
        '601011DIL.B Extended Coolant Premium RTU KPK Tote Warning 04-21-2022.docx',
        '601013PA EGAF KPK Tote Warning 04-21-2022.docx',
        '601013PACLR EGAF Clr  KPK Tote Warning 04-21-2022.docx',
        '602000 Boat Wash KPK Tote Warning 04-22-20.docx',
        '602001 Bilge Cleaner KPK Tote Warning 04-18-2022.docx',
        '602003 Hull Cleaner KPK Tote Warning 1-7-20.docx',
        '602005 Waterproofing KPK Tote Warning 04-18-2022.docx',
        '602009 Teak Cleaner KPK Tote Warning 04-18-2022.docx',
        '602010 TRT Lemon KPK Tote Warning 04-18-2022.docx',
        '602011 TRT Pine KPK Tote Warning 04-18-2022.docx',
        '602014 Diesel Fuel Water Absorber KPK Tote Warning 04-20-2022.docx',
        '602016 Boat Cover Cleaner KPK Tote Warning 04-18-2022.docx',
        '602017 Deck Cleaner Tote Warning .docx',
        '602020 Barnacle Remover-Boat Bottom Cleaner KPK Tote Warning 12-19-19.docx',
        '602021 Water Spot Remover KPK Tote Warning 04-20-2022.docx',
        '602022 Rust Eater Converter KPK Tote Warning 1-7-20.docx',
        '602023 Vinyl Brite KPK Tote Warning 04-20-2022.docx',
        '602024 Rain View KPK Tote Warning 1-20-2020.docx',
        '602025KPK KPK Tote Warning 2-5-2020.docx',
        '602026KPK KPK Tote Warning 10-29-2024.docx',
        '602028KPK KPK Tote Warning 10-23-2024.docx',
        '602029 Fogging Oil KPK Tote Warning 04-18-2022.docx',
        '602030 Descaling Engine Flush KPK Tote Warning 1-28-20.docx',
        '602032Carb Teak Oil Tote Warning 04-19-21.docx',
        '602032SIKA Teak Oil Tote Warning 05-19-22.docx',
        '602033KPK EZ Store Start KPK Tote Warning 04-20-2022.docx',
        '602034KPK  Tote Warning 10-15-2024.docx',
        '602037 MSR KPK Tote Warning 12-18-19.docx',
        '602037EURO MSR KPK Tote Warning 12-18-19.docx',
        '602042 Aqua Clean KPK Tote Warning 04-19-2022.docx',
        '602043Purple Boat Wash & Wax KPK Tote Warning 04-22-20.docx',
        '602045 Carpet Clean KPK Tote Warning 04-20-2022.docx',
        '602046 Boat Soap KPK Tote Warning 04-22-20 (AutoRecovered).docx',
        '602046 Boat Soap KPK Tote Warning 04-22-20.docx',
        '602047 Pink Bilge Cleaner KPK Tote Warning 01-25-2024.docx',
        '602058.B Magma Grill Restorer KPK Tote Warning 1-7-20.docx',
        '602059 Eco Trim ANd Tilt KPK Tote Warning 04-18-2022.docx',
        '602066 Plastic Clnr & Restorer KPK Tote Warning 05-23-2022.docx',
        '602067 Bowl & Drain Cleaner KPK Tote Warning 04-20-2022.docx',
        '602068 Eco Head Lube KPK Tote Warning 04-18-2022.docx',
        '602070 10W30 KPK Tote Warning 04-18-2022.docx',
        '602071 Full Syn 10W40 KPK Tote Warning 04-18-2022.docx',
        '602072 Full Syn 20W40 KPK Tote Warning 04-18-2022.docx',
        '602077 Concentrated Deck Cleaner KPK Tote Warning 04-20-2022.docx',
        '602082 Low Odor Waterproofing KPK Tote Warning 04-21-2022.docx',
        '602090 Waterproofing KPK Tote Warning 08-17-2023.docx',
        '602095.B Eco Waterproofing PFAS Free Tote Warning 04-20-2022.docx',
        '602111 Waterproofing Water Based KPK Tote Warning 05-08-2024.docx',
        '602602.B Mildew Stain Remover - GEL Formula KPK Tote Warning 1-7-20.docx',
        '602604 Citrus Boat Soap KPK Tote Warning 04-18-2022.docx',
        '602605 Citrus Bilge Clnr KPK Tote Warning 04-18-2022.docx',
        '602607CONC WM Descaler Conc KPK Tote Warning 02-09-21.docx',
        '602607RTU WM Descaler RTU KPK Tote Warning 02-09-21.docx',
        '602609 TS Purple Car Wash KPK Tote Warning 03-13-2024.docx',
        '63568CONC.B KPK Tote Warning 12-7-2023.docx',
        '63568RTU.B KPK Tote Warning 12-7-2023.docx',
        '7-2738.B Spray Fast Wax KPK Tote Warning 04-21-2022.docx',
        '81500 Teak Brightener KPK Tote Warning 1-7-20.docx',
        '83200.B Extreme Clean KPK Tote Warning 4-19-2022.docx',
        '84200.B Xtreme Clnr Degrs KPK Tote Warning 11-20-2023.docx',
        '86600.B Mildew Stain Blocker KPK Tote Warning 04-21-2022.docx',
        '86700.B Rub Rail Restorer KPK Tote Warning 04-20-2022.docx',
        '87700.B Ultimate Aluminum Cleaner KPK Tote Warning 12-19-19.docx',
        '88300.B Screen Cleaner Protector KPK Tote Warning 04-21-2022.docx',
        '89755.B Sea Safe Waterproofing KPK Tote Warning 04-20-2022.docx',
        '90400.B Violet Boat Wash KPK Tote Warning 06-07-23.docx',
        '91000.B Inflatable Boat Cleaner Vinyl Polish KPK Tote Warning 04-20-2022.docx',
        '92000.B Water Spot Remover KPK Tote Warning 04-18-2022.docx',
        '93100DSL.B  Startron Diesel KPK Tote Warning 04-18-2022.docx',
        '93100GAS.B  Startron Gas KPK Tote Warning 04-18-2022.docx',
        '93100GASBLUE.B Sierra Startron Gas KPK Tote Warning 04-20-2022.docx',
        '93100Tank.B Startron DSL Fuel  KPK Tote Warning 04-20-2022.docx',
        '93100XBEE.B Xbee Fuel KPK Tote Warning 04-20-2022.docx',
        '93700.B Power Pine Boat Wash  KPK Tote Warning 05-04-2022.docx',
        '93800.B Power Pine Bilge Cleaner  KPK Tote Warning 04-20-2022.docx',
        '94200.B Orange Purpose Cleaner Degreaser KPK Tote Warning 04-21-2022.docx',
        '94200CLEAR.B Purpose Cleaner Degreaser KPK Tote Warning 04-21-2022.docx',
        '94400.B Super Orange Citrus Bilge Cleaner KPK Tote Warning 04-18-2022.docx',
        '94444CON.B Salt Off Con KPK Tote Warning 04-18-2022.docx',
        '94444RTU.B Salt Off RTU KPK Tote Warning 04-19-2022.docx',
        '94500.B Super Orange Citrus Boat Wash KPK Tote Warning 04-20-2022.docx',
        '94600.B  Super Orange Citrus Boat Wash & Wax KPK Tote Warning 04-18-2022.docx',
        '94700.B PP Wash and Wax KPK Tote Warning 04-20-2022.docx',
        '94900.B Teak Cleaner & Brightener KPK Tote Warning 1-20-2020.docx',
        '95000.B View Guard KPK Tote Warning 04-18-2022.docx',
        '95022.B Spider Away KPK Tote Warning 1-20-20.docx',
        '95300.B Odor Guard KPK Tote Warning 04-21-2022.docx',
        '95400.B Corrosion Block KPK Tote Warning 04-20-2022.docx',
        '95500.B LPC Diesel Additive KPK Tote Warning 4-19-2022.docx',
        '95600.B RIng Cleaner KPK Tote Warning 04-20-2022.docx',
        '95900.B Vinyl Guard  KPK Tote Warning 04-20-2022.docx',
        '96100.B Gel Hull Clnr KPK Tote Warning 1-21-20.docx',
        '964 Sticker On KPK Tote Warning 05-23-2022.docx',
        '96500.B Tea Tree Oil Spray KPK Tote Warning 04-20-2022.docx',
        '965GEL.B Tea Tree Gel KPK Tote Warning 6-20-23.docx',
        '97000DIL.B Water Treatment Freshner KPK Tote Warning 04-20-2022.docx',
        '97100.B Water Shock KPK Tote Warning 04-20-2022.docx',
        '97200.B Inf. Boat Clnr KPK Tote Warning 06-02-2022.docx',
        '97300.B Non-Skid Deck Wax KPK Tote Warning 04-18-2022.docx',
        'FLUSH KPK Tote Warning 04-18-2022.docx',
        'K4199-1.B Lincoln Elec AF KPK Tote Warning 04-20-2022.docx',
        'KA00116.B Super K Conc Winshield Washer Fluid KPK Tote Warning 04-21-2022.docx',
        'Oil Waste KPK Tote Warning 04-18-2022.docx',
        'TEAK SEALER FLUSH KPK Tote Warning 07-07-2022.docx']

        # Your Excellency, allow me to assist in purging those pesky blend items that already have their documentation...
        
    blend_items_list = [item[0] for item in blend_items]
    
    for filename in filenames:
        # Check if any blend item codes are contained in the filename
        for item_code in blend_items_list[:]:
            if item_code in filename:
                blend_items_list.remove(item_code)
                break
                
    print("\nRemaining blend items without GHS files:")
    for item in blend_items_list:
        print(item)
