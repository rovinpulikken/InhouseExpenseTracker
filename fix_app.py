with open('app.py', 'r') as f:
    content = f.read()

# Fix 1: add import
import_target = "    clear_recovery_otp\n)"
import_repl = "    clear_recovery_otp,\n    get_admin_gemini_api_key\n)"
content = content.replace(import_target, import_repl)

# Fix 2: line 935
target_2 = '                gemini_api_key = current_user.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "") or st.secrets.get("GEMINI_API_KEY", "")'
repl_2 = '                gemini_api_key = current_user.get("gemini_api_key") or get_admin_gemini_api_key() or os.environ.get("GEMINI_API_KEY", "") or st.secrets.get("GEMINI_API_KEY", "")'
content = content.replace(target_2, repl_2)

# Fix 3: line 2283
target_3 = '''                default_api_key = current_user.get("gemini_api_key")
                if not default_api_key:
                    default_api_key = os.environ.get("GEMINI_API_KEY", "")
                if not default_api_key:
                    try:
                        default_api_key = st.secrets.get("GEMINI_API_KEY", "")
                    except Exception:
                        pass'''
repl_3 = '''                default_api_key = current_user.get("gemini_api_key")
                if not default_api_key:
                    default_api_key = get_admin_gemini_api_key()
                if not default_api_key:
                    default_api_key = os.environ.get("GEMINI_API_KEY", "")
                if not default_api_key:
                    try:
                        default_api_key = st.secrets.get("GEMINI_API_KEY", "")
                    except Exception:
                        pass'''
content = content.replace(target_3, repl_3)

# Fix 4: line 2933
target_4 = '''            gemini_api_key = (
                current_user.get("gemini_api_key") or
                os.environ.get("GEMINI_API_KEY", "") or
                st.secrets.get("GEMINI_API_KEY", "")
            )'''
repl_4 = '''            gemini_api_key = (
                current_user.get("gemini_api_key") or
                get_admin_gemini_api_key() or
                os.environ.get("GEMINI_API_KEY", "") or
                st.secrets.get("GEMINI_API_KEY", "")
            )'''
content = content.replace(target_4, repl_4)

# Fix 5: line 3858
target_5 = '''        gemini_api_key = (
            current_user.get("gemini_api_key") or
            os.environ.get("GEMINI_API_KEY", "") or
            st.secrets.get("GEMINI_API_KEY", "")
        )'''
repl_5 = '''        gemini_api_key = (
            current_user.get("gemini_api_key") or
            get_admin_gemini_api_key() or
            os.environ.get("GEMINI_API_KEY", "") or
            st.secrets.get("GEMINI_API_KEY", "")
        )'''
content = content.replace(target_5, repl_5)

with open('app.py', 'w') as f:
    f.write(content)
