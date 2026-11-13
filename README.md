RetailPulse · Retail Sales and Inventory ETL
A small shop exports sales and stock data as CSV files. RetailPulse turns those files into three reports the owner can use to see daily revenue, identify best sellers, and decide which products to review for restocking.
Run the demo
Install Python 3.10 or newer. SQLite comes with Python, and the project has no additional dependencies.

Clone the repository and open its folder:
git clone https://github.com/AmanCodes11/retailpulse-etl.git
cd retailpulse-etl
If you don't have Git, choose Code → Download ZIP on this repository page, extract the download, and open the folder containing pipeline.py.

Run the pipeline from that folder. On Windows:
py pipeline.py
On macOS or Linux:
python3 pipeline.py
The script creates retailpulse.db and prints all three reports plus the rejected sales. The synthetic demo has 5 products, 6 valid sale lines, and 4 rejected rows.
Date	Revenue
2026-11-10	₹1,076.50
2026-11-11	₹406.00
2026-11-12	₹470.00


Low-stock products are biscuits (0 in stock), tea (2), and rice (3). Tea is flagged because the rule includes stock equal to the reorder threshold.
How it works
Step	What happens	Where to look
Extract	Read the complete product and sales CSV files.	data/, read_csv()
Transform	Trim text, standardize IDs, validate dates and quantities, and convert prices to integer paise. Keep the first valid row for each sale ID and record rejected rows with reasons.	extract_products(), extract_sales()
Load	Refresh the SQLite tables in one transaction. Primary keys enforce uniqueness and a foreign key links each sale to its product.	schema.sql, load_snapshot()
Report	Use SQL views, a left join, grouping, and aggregates to answer the three business questions.	reports.sql


Each sales row represents one product sale line. Stock comes from the product snapshot, which can reflect replenishment and adjustments. The pipeline does a full refresh, so keep all sales you want reported in sales.csv. Running the same input twice keeps the same row counts. A bad product master or malformed CSV stops the run before the data refresh. Invalid individual sale rows with parseable CSV structure go into rejected_sales.
Try it yourself
In products.csv, change the stock for rice from 3 to 6. Rerun the pipeline and check that rice disappears from low stock while its revenue stays the same. Then trace the duplicated sale ID S006 from sales.csv through the rejection report. You can open the generated database in a SQLite viewer and run:
SELECT sale_date, revenue_paise / 100.0 AS revenue_inr
FROM daily_revenue
ORDER BY sale_date;
