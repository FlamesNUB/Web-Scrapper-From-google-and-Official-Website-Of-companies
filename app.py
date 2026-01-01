from flask import Flask, render_template, request, jsonify, send_file
from finalscript import scrape_google_news_links  # Import from finalscript
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        company_ids = request.form.get('company_ids')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        max_pages = int(request.form.get('max_pages', 5))
        
        if not company_ids or not start_date or not end_date:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Convert dates from YYYY-MM-DD (HTML) to MM-DD-YYYY (scraper format)
        start_date_formatted = datetime.strptime(start_date, '%Y-%m-%d').strftime('%m-%d-%Y')
        end_date_formatted = datetime.strptime(end_date, '%Y-%m-%d').strftime('%m-%d-%Y')
        
        company_list = [company.strip() for company in company_ids.split(",") if company.strip()]
        
        all_results = []
        for company_id in company_list:
            links = scrape_google_news_links(
                company_id=company_id,
                start_date=start_date_formatted,
                end_date=end_date_formatted,
                max_pages=max_pages
            )
            all_results.extend([{"Company_ID": company_id, "Link": link} for link in links])
        
        if not all_results:
            return jsonify({'error': 'No links found'}), 404
        
        # Create Excel file
        filename = f"filtered_news_links_{start_date}to{end_date}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
        filepath = os.path.join('static', 'downloads', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        pd.DataFrame(all_results).to_excel(filepath, index=False)
        
        return jsonify({
            'success': True,
            'count': len(all_results),
            'download_url': f'/download/{filename}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    return send_file(
        os.path.join('static', 'downloads', filename),
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    app.run(debug=True)