"""Offline check. Feeds fixture HTML through the whole pipeline so you can see
the board and the message without touching the network.

    python -m tests.offline_test
"""
from __future__ import annotations

import sys
from datetime import date, timedelta

from src import fetcher, main as runner
from src.scrapers import pesb, pagewatch
from src.notify import compose, channels
from src.dashboard import render
from src.store import Store

TODAY = date.today()


def d(offset):
    return (TODAY + timedelta(days=offset)).strftime("%d.%m.%Y")


PESB_HTML = f"""
<html><body><table class="table">
<tr><th>Sl. No.</th><th>Name of the CPSE</th><th>Post / JD / Issue Date</th>
    <th>Sch. of the CPSE</th><th>Pay Scale(Rs.) / Vacancy Date</th>
    <th>Last Date for Applicants</th></tr>
<tr><td>1</td><td>IRCON International Limited</td>
    <td><a href="/JobDescription/1234">Director (Works) Job Description</a>
        <img src="pdf.png"> {d(-20)}</td>
    <td>Schedule A</td><td>Rs. 180000 - 340000 (IDA) {d(120)}</td>
    <td>{d(4)} 3:00PM <a href="/Apply/1234">Apply</a></td></tr>
<tr><td>2</td><td>Rail Vikas Nigam Limited</td>
    <td><a href="/JobDescription/1235">Chairman &amp; Managing Director
        Job Description</a> {d(-6)}</td>
    <td>Schedule A</td><td>Rs. 200000 - 370000 (IDA) {d(200)}</td>
    <td>{d(22)} 3:00PM <a href="/Apply/1235">Apply</a></td></tr>
<tr><td>3</td><td>Konkan Railway Corporation Limited</td>
    <td><a href="/JobDescription/1236">Director (Way &amp; Works)
        Job Description</a> {d(-2)}</td>
    <td>Schedule A</td><td>Rs. 180000 - 340000 (IDA) {d(90)}</td>
    <td>{d(26)} 3:00PM</td></tr>
<tr><td>4</td><td>Steel Authority of India Limited (SAIL)</td>
    <td><a href="/JobDescription/1237">Director (Commercial)</a> {d(-3)}</td>
    <td>Schedule A</td><td>Rs. 180000 - 340000 (IDA) {d(60)}</td>
    <td>{d(25)} 3:00PM</td></tr>
<tr><td>5</td><td>Dedicated Freight Corridor Corporation of India Limited</td>
    <td><a href="/JobDescription/1238">Director (Operations &amp; Business
        Development)</a> {d(-40)}</td>
    <td>Schedule A</td><td>Rs. 180000 - 340000 (IDA) {d(-5)}</td>
    <td>{d(-9)} 3:00PM</td></tr>
</table></body></html>"""

UPCOMING_HTML = f"""
<html><body><table>
<tr><th>Sl</th><th>Name of the CPSE</th><th>Post</th><th>Schedule</th>
    <th>Vacancy Date</th><th>Last Date</th></tr>
<tr><td>1</td><td>RITES Limited</td><td>Director (Projects)</td>
    <td>Schedule A</td><td>{d(150)}</td><td></td></tr>
<tr><td>2</td><td>Container Corporation of India Limited</td>
    <td>Chairman &amp; Managing Director</td><td>Schedule A</td>
    <td>{d(240)}</td><td></td></tr>
</table></body></html>"""

CAREER_V1 = """<html><body><h2>Careers</h2><ul>
<li><a href="/docs/old-notice.pdf">Recruitment of Manager (Civil) 2025</a></li>
</ul></body></html>"""

CAREER_V2 = """<html><body><h2>Careers</h2><ul>
<li><a href="/docs/old-notice.pdf">Recruitment of Manager (Civil) 2025</a></li>
<li><a href="/docs/ed-civil.pdf">Engagement of Executive Director (Civil) on
    deputation basis — 15.08.2026</a></li>
</ul></body></html>"""

FIXTURES = {
    "https://pesb.gov.in/Home/AdvertisVacancy": PESB_HTML,
    "https://pesb.gov.in/Advertisement/UpcomingVacancyDetailsForAll": UPCOMING_HTML,
}


def fake_get(url):
    if url in FIXTURES:
        return True, FIXTURES[url], ""
    if "delhimetrorail" in url:
        return True, fake_get.career, ""
    return False, "", "simulated network failure"


def run():
    fake_get.career = CAREER_V1
    fetcher.get = fake_get
    runner.fetcher.get = fake_get

    print("=== PASS 1 (first run: baseline) " + "=" * 28)
    sys.argv = ["x", "--dry-run", "--demo"]
    runner.main()

    print("\n=== PASS 2 (a new PDF appears on the DMRC page) " + "=" * 13)
    fake_get.career = CAREER_V2
    sys.argv = ["x", "--dry-run", "--demo"]
    runner.main()


if __name__ == "__main__":
    run()
