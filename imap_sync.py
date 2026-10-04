import imaplib
import email
from email.header import decode_header
import datetime
import pandas as pd
import streamlit as st
from statement_parser import parse_expense_statement_with_gemini

def fetch_recent_transaction_emails(imap_username, imap_password, days=3):
    """
    Connects to IMAP server and fetches recent emails from known payment providers.
    Returns a list of dictionaries with date, subject, and body text.
    """
    if not imap_username or not imap_password:
        raise ValueError("IMAP email or app password is not configured in your profile.")
        
    server = "imap.gmail.com"
    port = 993
    
    mail = imaplib.IMAP4_SSL(server, port)
    mail.login(imap_username, imap_password)
    mail.select("inbox")
    
    date_since = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
    
    # Search for common payment providers
    # In IMAP, OR is tricky. Let's just search by SUBJECT "paid" or "debited" or from google/amazon
    # We will do a generic search for emails in the last N days and filter in Python to avoid IMAP dialect issues.
    status, messages = mail.search(None, f'(SINCE {date_since})')
    
    if status != "OK":
        return []
        
    email_ids = messages[0].split()
    transaction_emails = []
    
    for e_id in email_ids[-50:]: # Process at most last 50 emails to avoid timeout
        res, msg_data = mail.fetch(e_id, '(RFC822)')
        if res != "OK":
            continue
            
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg.get("Subject", ""))[0]
                if isinstance(subject, bytes):
                    try:
                        subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")
                    except:
                        subject = str(subject)
                        
                sender = msg.get("From", "")
                
                # Check if it's a payment email
                sender_lower = sender.lower()
                subj_lower = subject.lower()
                
                is_payment = ("googlepay" in sender_lower or 
                              "amazonpay" in sender_lower or 
                              "paid" in subj_lower or 
                              "debited" in subj_lower or 
                              "transaction" in subj_lower or
                              "ordered" in subj_lower or
                              "statement" in subj_lower)
                              
                if not is_payment:
                    continue
                
                def filename_attr(part):
                    fname = part.get_filename()
                    if fname:
                        fname, enc = decode_header(fname)[0]
                        if isinstance(fname, bytes):
                            fname = fname.decode(enc if enc else 'utf-8', errors='ignore')
                        return str(fname)
                    return ""
                
                
                # Extract body and attachments
                body = ""
                pdf_attachments = []
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            try:
                                if not body: # Prefer first text/plain part
                                    body = part.get_payload(decode=True).decode()
                            except:
                                pass
                        elif content_type == "application/pdf" or filename_attr(part).lower().endswith(".pdf"):
                            try:
                                pdf_bytes = part.get_payload(decode=True)
                                fname = filename_attr(part) or "statement.pdf"
                                pdf_attachments.append({"filename": fname, "bytes": pdf_bytes})
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()
                    except:
                        pass
                
                if body or pdf_attachments:
                    transaction_emails.append({
                        "subject": subject,
                        "sender": sender,
                        "date": msg.get("Date"),
                        "body": body,
                        "pdf_attachments": pdf_attachments
                    })
                    
    mail.logout()
    return transaction_emails

def parse_emails_to_dataframe(emails_list, api_key, pdf_password=""):
    """
    Passes the combined email text and any PDF attachments to Gemini to parse into structured transactions.
    """
    if not emails_list:
        return pd.DataFrame()
        
    all_parsed = []
        
    # Combine emails into a single text block to send to Gemini
    combined_text = ""
    for i, e in enumerate(emails_list):
        if e['body']:
            combined_text += f"\n--- EMAIL {i+1} ---\n"
            combined_text += f"Date: {e['date']}\nSender: {e['sender']}\nSubject: {e['subject']}\nBody:\n{e['body']}\n"
        
    # We use a dummy CSV filename so statement_parser sets mime_type='text/csv' but it processes plain text just fine
    if combined_text:
        dummy_filename = "email_sync.csv"
        try:
            parsed_json = parse_expense_statement_with_gemini(
                file_bytes=combined_text.encode('utf-8'),
                filename=dummy_filename,
                api_key=api_key,
                pdf_password=""
            )
            if parsed_json:
                all_parsed.extend(parsed_json)
        except Exception as e:
            print(f"Error parsing email text: {e}")
            
    # Process PDF attachments
    for e in emails_list:
        for attachment in e.get("pdf_attachments", []):
            try:
                parsed_pdf = parse_expense_statement_with_gemini(
                    file_bytes=attachment["bytes"],
                    filename=attachment["filename"],
                    api_key=api_key,
                    pdf_password=pdf_password
                )
                if parsed_pdf:
                    all_parsed.extend(parsed_pdf)
            except Exception as ex:
                print(f"Error parsing PDF attachment {attachment['filename']}: {ex}")
    
    df = pd.DataFrame(all_parsed)
    if not df.empty:
        df["_source_file"] = "IMAP Sync"
    return df
