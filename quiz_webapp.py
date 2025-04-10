import streamlit as st
import csv
import random
import pandas as pd
from collections import defaultdict

# --- Configuration ---
QUIZ_PASSWORD = "aatw"
CSV_FILENAME = "test_bank.csv" # Assumes the CSV is in the same directory

# --- Air Force Theme Configuration (Basic) ---
st.set_page_config(layout="wide")
primaryColor = "#00308F"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#D6E6F2"
textColor = "#0B0B0B"
font = "sans serif"
try:
    st.config.set_option('theme.primaryColor', primaryColor)
    st.config.set_option('theme.backgroundColor', backgroundColor)
    st.config.set_option('theme.secondaryBackgroundColor', secondaryBackgroundColor)
    st.config.set_option('theme.textColor', textColor)
    st.config.set_option('theme.font', font)
except Exception as e:
    st.warning(f"Could not apply theme settings directly: {e}. Using defaults.")

# --- Data Loading Function ---
@st.cache_data(show_spinner=False) # Cache the loaded data
def load_and_process_questions(filename):
    """Loads questions and categorizes them by type and matching group."""
    questions_by_type = defaultdict(list)
    matching_groups = defaultdict(list)
    all_questions_list = []
    
    try:
        # Simple CSV reading approach without pandas to reduce complexity
        with open(filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader, None)  # Get headers
            
            # Map column indices based on the provided headers
            # Default mappings based on your header: Type,Question,CorrectAnswer,Distractor1,Distractor2,Distractor3,Explanation
            type_idx = 0  # 'Type' column
            question_idx = 1  # 'Question' column
            answer_idx = 2  # 'CorrectAnswer' column
            exp_idx = 6  # 'Explanation' column
            
            # For MCQ, record distractor columns
            distractor_indices = [3, 4, 5]  # 'Distractor1', 'Distractor2', 'Distractor3'
            
            # Process rows
            row_index = 0
            for row in reader:
                if not row or len(row) < 3:  # Skip rows with insufficient data
                    continue
                
                try:
                    q_type = row[type_idx].strip() if type_idx < len(row) else ''
                    
                    if q_type.lower() == 'matching':
                        # Handle matching question
                        question_text = row[question_idx].strip() if question_idx < len(row) else ''
                        
                        # Extract the group name from the question 
                        # Assuming format: "Match terms for group: [Group Name]" or just the group name
                        group = ''
                        if ":" in question_text:
                            parts = question_text.split(":", 1)
                            if len(parts) > 1:
                                group = parts[1].strip()
                            else:
                                group = question_text.strip()
                        else:
                            group = question_text.strip()
                        
                        # For matching questions, the term will be in the term_idx column (CorrectAnswer in this case)
                        term = row[answer_idx].strip() if answer_idx < len(row) else ''
                        
                        # For matching, we need definitions - these would be in the distractor columns
                        definition = ''
                        for idx in distractor_indices:
                            if idx < len(row) and row[idx].strip():
                                definition = row[idx].strip()
                                break
                        
                        explanation = row[exp_idx].strip() if exp_idx < len(row) and len(row) > exp_idx else ''
                        
                        if group and term:
                            # Create question dict with all required fields
                            question_dict = {
                                'Type': 'Matching',
                                'Group': group,
                                'Term': term,              # This is the abbreviation (left side)
                                'Question': question_text, # Original question text
                                'Definition': definition,  # This is the explanation (right side)
                                'CorrectAnswer': definition,  # For grading consistency
                                'Explanation': explanation,
                                'original_index': row_index
                            }
                            
                            # Add to collections
                            matching_groups[group].append(question_dict)
                            questions_by_type['Matching'].append(question_dict)
                            all_questions_list.append(question_dict)
                            row_index += 1
                    
                    elif q_type in ['MCQ', 'TF', 'FillBlank']:
                        # Handle other question types
                        question = row[question_idx].strip() if question_idx < len(row) else ''
                        answer = row[answer_idx].strip() if answer_idx < len(row) else ''
                        explanation = row[exp_idx].strip() if exp_idx < len(row) and len(row) > exp_idx else ''
                        
                        # Create basic question dictionary
                        question_dict = {
                            'Type': q_type,
                            'Question': question,
                            'CorrectAnswer': answer,
                            'Explanation': explanation,
                            'original_index': row_index
                        }
                        
                        # Handle type-specific processing
                        if q_type == 'MCQ':
                            # Get distractors from specified columns
                            distractors = []
                            for idx in distractor_indices:
                                if idx < len(row) and row[idx].strip():
                                    distractors.append(row[idx].strip())
                            
                            question_dict['Distractors'] = distractors
                        
                        elif q_type == 'TF':
                            # Convert to boolean
                            question_dict['CorrectAnswer'] = answer.lower() == 'true'
                        
                        # Add to collections
                        questions_by_type[q_type].append(question_dict)
                        all_questions_list.append(question_dict)
                        row_index += 1
                except Exception as row_error:
                    # Skip problematic rows but continue processing
                    pass
    
    except FileNotFoundError:
        st.error(f"Error: File '{filename}' not found. Please ensure the file '{filename}' is in the same directory as your app.")
        empty_result = (dict(questions_by_type), dict(matching_groups), all_questions_list)
        return empty_result  # Return empty collections
        
    except Exception as e:
        # Log error but return empty collections
        st.error(f"Error reading CSV: {str(e)}")
        st.error(f"Make sure '{filename}' is a valid CSV file with the correct format.")
        empty_result = (dict(questions_by_type), dict(matching_groups), all_questions_list)
        return empty_result  # Return empty collections

    # Always return a valid tuple of results
    return dict(questions_by_type), dict(matching_groups), all_questions_list


# --- Initialize Session State ---
def init_session_state():
    # Set logged_in to True by default to bypass login screen
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = True
    
    # Question Data
    if 'questions_by_type' not in st.session_state:
        st.session_state.questions_by_type = {}
    if 'matching_groups_data' not in st.session_state:
        st.session_state.matching_groups_data = {} # Store grouped matching questions
    if 'available_counts' not in st.session_state:
        st.session_state.available_counts = {}
    if 'selected_counts' not in st.session_state:
        st.session_state.selected_counts = {} # {q_type: count}
    if 'selected_matching_groups' not in st.session_state:
        st.session_state.selected_matching_groups = [] # List of group names chosen

    # Quiz State
    if 'setup_complete' not in st.session_state:
        st.session_state.setup_complete = False # New flag for setup screen
    if 'quiz_pool' not in st.session_state:
        st.session_state.quiz_pool = [] # The final list of questions for this quiz session
    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {} # {index_in_quiz_pool: answer}
    if 'flagged_questions' not in st.session_state:
        st.session_state.flagged_questions = {} # {index_in_quiz_pool: bool}
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    if 'shuffled_mcq_options' not in st.session_state:
        st.session_state.shuffled_mcq_options = {} # {index_in_quiz_pool: [options_list]}
    if 'matching_answers' not in st.session_state:
        st.session_state.matching_answers = {}  # Will store {question_idx: {term_idx: selected_definition_idx}}
    if 'shuffled_matching_definitions' not in st.session_state:
        st.session_state.shuffled_matching_definitions = {}  # {q_idx_pool: shuffled_definitions_list}
    
    # Learning Mode State
    if 'learning_mode' not in st.session_state:
        st.session_state.learning_mode = False  # Flag for learning mode
        
    # Load questions immediately
    if not st.session_state.questions_by_type:
        try:
            questions_by_type, matching_groups_data, all_questions = load_and_process_questions(CSV_FILENAME)
            
            # Make sure we got valid data
            if questions_by_type and isinstance(questions_by_type, dict):
                st.session_state.questions_by_type = questions_by_type
                st.session_state.matching_groups_data = matching_groups_data
                
                # Calculate available counts (excluding matching initially)
                st.session_state.available_counts = {
                    q_type: len(q_list) for q_type, q_list in questions_by_type.items() if q_type != 'Matching'
                }
                
                # Initialize selected counts
                st.session_state.selected_counts = {
                    q_type: 0 for q_type in st.session_state.available_counts
                }
                
                st.session_state.selected_matching_groups = []  # Reset selected groups
            else:
                st.error(f"Could not process question data from {CSV_FILENAME}. Check file format.")
        except Exception as e:
            st.error(f"Error loading questions: {str(e)}")

# --- Callback Functions ---
def check_login():
    if st.session_state.password_attempt == QUIZ_PASSWORD:
        st.session_state.logged_in = True
        st.session_state.password_attempt = ""  # Clear password attempt
        
        # Load questions immediately after login to prepare for setup
        try:
            questions_by_type, matching_groups_data, all_questions = load_and_process_questions(CSV_FILENAME)
            
            # Make sure we got valid data
            if questions_by_type and isinstance(questions_by_type, dict):
                st.session_state.questions_by_type = questions_by_type
                st.session_state.matching_groups_data = matching_groups_data
                
                # Calculate available counts (excluding matching initially)
                st.session_state.available_counts = {
                    q_type: len(q_list) for q_type, q_list in questions_by_type.items() if q_type != 'Matching'
                }
                
                # Initialize selected counts
                st.session_state.selected_counts = {
                    q_type: 0 for q_type in st.session_state.available_counts
                }
                
                st.session_state.selected_matching_groups = []  # Reset selected groups
            else:
                st.error(f"Could not process question data from {CSV_FILENAME}. Check file format.")
                st.session_state.logged_in = False  # Prevent login if data is invalid
        except Exception as e:
            st.error(f"Error loading questions: {str(e)}")
            st.session_state.logged_in = False  # Prevent login if an error occurs
    else:
        if st.session_state.password_attempt:  # Only show error if attempt was made
            st.error("Incorrect password.")
        st.session_state.logged_in = False

def start_quiz():
    """Builds the quiz pool based on selected counts and groups, marks setup complete."""
    final_pool = []

    # Add MCQ, TF, FillBlank based on counts
    for q_type, questions in st.session_state.questions_by_type.items():
        if q_type == 'Matching': continue  # Handle matching separately

        count = st.session_state.selected_counts.get(q_type, 0)
        num_available = len(questions)
        actual_count = min(count, num_available)  # Ensure we don't request more than available

        if actual_count > 0:
            final_pool.extend(random.sample(questions, actual_count))

    # Add selected Matching groups as consolidated group questions (one per group)
    selected_groups = st.session_state.get('selected_matching_groups', [])
    for group_name in selected_groups:
        if group_name in st.session_state.matching_groups_data:
            # Get all terms for this group
            group_terms = st.session_state.matching_groups_data[group_name]
            
            if group_terms:
                # Create a single question object that represents the entire matching group
                matching_question = {
                    'Type': 'MatchingGroup',  # Different type to distinguish from individual matching items
                    'Group': group_name,
                    'Question': f"Match the following terms for: {group_name}",
                    'MatchingTerms': group_terms,  # Store all terms in this group
                    'TermCount': len(group_terms)
                }
                
                # Add just one question object for the entire group
                final_pool.append(matching_question)

    if not final_pool:
        st.warning("No questions selected. Please select at least one question or matching group.")
        return  # Don't start quiz if pool is empty

    random.shuffle(final_pool)  # Shuffle the order of questions
    st.session_state.quiz_pool = final_pool

    # Reset quiz state variables based on the new pool
    st.session_state.current_question_index = 0
    st.session_state.user_answers = {i: None for i in range(len(final_pool))}
    st.session_state.flagged_questions = {i: False for i in range(len(final_pool))}
    st.session_state.submitted = False
    st.session_state.shuffled_mcq_options = {}  # Reset shuffled options
    
    # Add a new state variable for matching answers
    st.session_state.matching_answers = {}  # Will store {question_idx: {term_idx: selected_definition_idx}}

    st.session_state.setup_complete = True  # Mark setup as done

def save_answer(q_idx_pool):
    """Saves the selected answer for the current question index in the quiz_pool."""
    if not st.session_state.quiz_pool or q_idx_pool >= len(st.session_state.quiz_pool): return
    q_data = st.session_state.quiz_pool[q_idx_pool]
    q_type = q_data.get('Type')
    widget_key = f"q_{q_idx_pool}" # Key for the input widget

    if widget_key in st.session_state:
        answer = st.session_state[widget_key]
        # Store answer appropriately (e.g., boolean for TF)
        if q_type == "TF":
            st.session_state.user_answers[q_idx_pool] = (answer == "True") # Store as bool
        else:
            st.session_state.user_answers[q_idx_pool] = answer # Store string/other

def toggle_flag(q_idx_pool):
    """Toggles the flag status for the current question index in the quiz_pool without navigating."""
    current_flag_status = st.session_state.flagged_questions.get(q_idx_pool, False)
    st.session_state.flagged_questions[q_idx_pool] = not current_flag_status

def navigate_question(new_index_pool):
    """Sets the current question index in the quiz_pool."""
    if 0 <= new_index_pool < len(st.session_state.quiz_pool):
        st.session_state.current_question_index = new_index_pool

def submit_quiz():
    """Sets the submission flag."""
    st.session_state.submitted = True

# --- Display Functions ---
def display_login():
    st.title("Quiz Login")
    st.text_input("Password", type="password", key="password_attempt", on_change=check_login, help=f"Default password is '{QUIZ_PASSWORD}'")
    st.button("Login", on_click=check_login)

def display_setup_screen():
    st.title("Quiz Setup")
    st.write("Select the number of questions for each type:")

    # --- Number Input for Standard Types ---
    supported_types = ["MCQ", "TF", "FillBlank"] # Define order
    for q_type in supported_types:
        available = st.session_state.available_counts.get(q_type, 0)
        if available > 0:
            st.session_state.selected_counts[q_type] = st.number_input(
                f"{q_type} (Max: {available})",
                min_value=0, max_value=available,
                value=st.session_state.selected_counts.get(q_type, 0),
                key=f"select_{q_type}"
            )
        else:
             st.write(f"No {q_type} questions available.")
    st.divider()

    # --- Checkboxes for Matching Groups ---
    st.subheader("Select Matching Groups to Include")
    available_matching_groups = sorted(st.session_state.matching_groups_data.keys())
    if not available_matching_groups:
        st.write("No Matching question groups available.")
    else:
        temp_selected_groups = []
        # Use columns for better layout if many groups
        cols = st.columns(3) # Adjust number of columns as needed
        col_idx = 0
        for group_name in available_matching_groups:
            num_terms = len(st.session_state.matching_groups_data[group_name])
            # Check if group was previously selected (persists across reruns within setup)
            is_selected = group_name in st.session_state.get('selected_matching_groups', [])
            with cols[col_idx % len(cols)]:
                if st.checkbox(f"{group_name} ({num_terms} terms)", value=is_selected, key=f"select_group_{group_name}"):
                    temp_selected_groups.append(group_name)
            col_idx += 1
        # Update the session state list based on current checkbox states
        st.session_state.selected_matching_groups = temp_selected_groups

    st.divider()
    
    # Add Learning Mode Option
    st.subheader("Quiz Mode")
    st.session_state.learning_mode = st.checkbox(
        "Learning Mode (Check answers as you go)",
        value=st.session_state.learning_mode,
        help="When enabled, you can check your answers immediately and see explanations during the quiz."
    )

    # Calculate total questions dynamically
    total_standard = sum(st.session_state.selected_counts.values())
    total_matching = sum(len(st.session_state.matching_groups_data[g]) for g in st.session_state.selected_matching_groups)
    total_selected = total_standard + total_matching

    st.write(f"**Total Questions Selected: {total_selected}** ({total_standard} Standard + {total_matching} Matching)")

    if st.button("Start Quiz", type="primary", disabled=(total_selected == 0)):
        start_quiz()
        st.rerun() # Rerun to move to the quiz display

def check_answer(q_idx_pool):
    """Marks the current question as checked for Learning Mode."""
    if not st.session_state.learning_mode:
        return
    
    st.session_state.checked_answers[q_idx_pool] = True

def display_sidebar_quiz():
    st.sidebar.title("Questions")
    total_questions = len(st.session_state.quiz_pool)
    st.sidebar.write(f"Total: {total_questions}")
    for i in range(total_questions):
        q_data = st.session_state.quiz_pool[i]
        q_type = q_data.get('Type','?')
        q_num_label = f"Q {i+1}"
        label = f"{q_num_label} ({q_type[:1]})" # Show Q number and Type initial

        status_icon = ""
        if st.session_state.user_answers.get(i) is not None: status_icon += " ✅"
        if st.session_state.flagged_questions.get(i, False): status_icon += " 🚩"

        button_label = f"{label}{status_icon}"
        button_type = "primary" if i == st.session_state.current_question_index else "secondary"

        if st.sidebar.button(button_label, key=f"nav_{i}", type=button_type, help=f"Type: {q_type}"):
            navigate_question(i)

    st.sidebar.divider()
    if st.sidebar.button("Submit Quiz", type="primary", use_container_width=True):
        submit_quiz()
        st.rerun()

def init_session_state():
    # Set logged_in to True by default to bypass login screen
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = True
    
    # Question Data
    if 'questions_by_type' not in st.session_state:
        st.session_state.questions_by_type = {}
    if 'matching_groups_data' not in st.session_state:
        st.session_state.matching_groups_data = {} # Store grouped matching questions
    if 'available_counts' not in st.session_state:
        st.session_state.available_counts = {}
    if 'selected_counts' not in st.session_state:
        st.session_state.selected_counts = {} # {q_type: count}
    if 'selected_matching_groups' not in st.session_state:
        st.session_state.selected_matching_groups = [] # List of group names chosen

    # Quiz State
    if 'setup_complete' not in st.session_state:
        st.session_state.setup_complete = False # New flag for setup screen
    if 'quiz_pool' not in st.session_state:
        st.session_state.quiz_pool = [] # The final list of questions for this quiz session
    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {} # {index_in_quiz_pool: answer}
    if 'flagged_questions' not in st.session_state:
        st.session_state.flagged_questions = {} # {index_in_quiz_pool: bool}
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    if 'shuffled_mcq_options' not in st.session_state:
        st.session_state.shuffled_mcq_options = {} # {index_in_quiz_pool: [options_list]}
    if 'matching_answers' not in st.session_state:
        st.session_state.matching_answers = {}  # Will store {question_idx: {term_idx: selected_definition_idx}}
    if 'shuffled_matching_definitions' not in st.session_state:
        st.session_state.shuffled_matching_definitions = {}  # {q_idx_pool: shuffled_definitions_list}
    
    # Learning Mode State
    if 'learning_mode' not in st.session_state:
        st.session_state.learning_mode = False  # Flag for learning mode
    if 'verified_matching_questions' not in st.session_state:
        st.session_state.verified_matching_questions = {}  # {q_idx_pool: bool} to track verified matching questions
        
    # Load questions immediately
    if not st.session_state.questions_by_type:
        try:
            questions_by_type, matching_groups_data, all_questions = load_and_process_questions(CSV_FILENAME)
            
            # Make sure we got valid data
            if questions_by_type and isinstance(questions_by_type, dict):
                st.session_state.questions_by_type = questions_by_type
                st.session_state.matching_groups_data = matching_groups_data
                
                # Calculate available counts (excluding matching initially)
                st.session_state.available_counts = {
                    q_type: len(q_list) for q_type, q_list in questions_by_type.items() if q_type != 'Matching'
                }
                
                # Initialize selected counts
                st.session_state.selected_counts = {
                    q_type: 0 for q_type in st.session_state.available_counts
                }
                
                st.session_state.selected_matching_groups = []  # Reset selected groups
            else:
                st.error(f"Could not process question data from {CSV_FILENAME}. Check file format.")
        except Exception as e:
            st.error(f"Error loading questions: {str(e)}")

def verify_matching_question(q_idx_pool):
    """Marks a matching question as verified for Learning Mode."""
    st.session_state.verified_matching_questions[q_idx_pool] = True

def display_question_quiz(q_idx_pool):
    if not st.session_state.quiz_pool or q_idx_pool >= len(st.session_state.quiz_pool):
        st.error("Invalid question index.")
        return

    question_data = st.session_state.quiz_pool[q_idx_pool]
    q_type = question_data.get('Type', 'N/A')
    question_text = question_data.get('Question', 'N/A')
    explanation = question_data.get('Explanation', 'No explanation provided.')

    st.subheader(f"Question {q_idx_pool + 1} of {len(st.session_state.quiz_pool)} ({q_type})")
    st.markdown(f"**{question_text}**")

    # --- Flag with Button Instead of Checkbox ---
    is_flagged = st.session_state.flagged_questions.get(q_idx_pool, False)
    flag_col1, flag_col2 = st.columns([1, 10])
    
    with flag_col1:
        flag_icon = "🚩" if is_flagged else "⚐"
        flag_text = "Remove Flag" if is_flagged else "Flag for Review"
        flag_button_key = f"flag_btn_{q_idx_pool}"
        
        if st.button(flag_icon, key=flag_button_key):
            # Toggle flag state
            st.session_state.flagged_questions[q_idx_pool] = not is_flagged
            st.rerun()  # Rerun to update UI immediately
    
    with flag_col2:
        st.write(flag_text)
    
    st.divider()

    # --- Answer Input based on Type ---
    current_answer = st.session_state.user_answers.get(q_idx_pool)
    has_answer = current_answer is not None
    is_verified = False  # For matching questions

    if q_type == 'MCQ':
        correct_answer = question_data.get('CorrectAnswer', 'N/A')
        distractors = question_data.get('Distractors', [])
        options = distractors + [correct_answer]

        # Shuffle options only once per question
        if q_idx_pool not in st.session_state.shuffled_mcq_options:
            random.shuffle(options)
            st.session_state.shuffled_mcq_options[q_idx_pool] = options
        else:
            options = st.session_state.shuffled_mcq_options[q_idx_pool]

        try: 
            current_selection_index = options.index(current_answer) if current_answer in options else None
        except ValueError: 
            current_selection_index = None

        answer = st.radio(
            "Choose the best answer:", options, index=current_selection_index,
            key=f"q_{q_idx_pool}", label_visibility='collapsed',
            on_change=save_answer, args=(q_idx_pool,)
        )
        
        # Save answer directly without on_change to avoid duplication
        if not has_answer:
            st.session_state.user_answers[q_idx_pool] = answer

    elif q_type == 'TF':
        options = ["True", "False"]
        current_selection_index = 0 if current_answer is True else 1 if current_answer is False else None
        
        answer = st.radio(
            "Select True or False:", options, index=current_selection_index,
            key=f"q_{q_idx_pool}", label_visibility='collapsed',
            on_change=save_answer, args=(q_idx_pool,)
        )
        
        # Convert string to boolean and save for initial answer
        if not has_answer:
            if answer == "True":
                st.session_state.user_answers[q_idx_pool] = True
            elif answer == "False":
                st.session_state.user_answers[q_idx_pool] = False

    elif q_type == 'FillBlank':
        answer = st.text_input(
            "Enter your answer:", value=current_answer if current_answer else "",
            key=f"q_{q_idx_pool}", on_change=save_answer, args=(q_idx_pool,)
        )
        
        # Save answer directly for initial value
        if not has_answer and answer:
            st.session_state.user_answers[q_idx_pool] = answer

    elif q_type == 'MatchingGroup':
        group_name = question_data.get('Group', 'Unknown Group')
        matching_terms = question_data.get('MatchingTerms', [])
        
        st.write(f"**Matching Group: {group_name}**")
        st.write("Match each term on the left with its definition on the right.")
        
        # Initialize matching answers for this question if needed
        if q_idx_pool not in st.session_state.matching_answers:
            st.session_state.matching_answers[q_idx_pool] = {}
        
        # Get all definitions and shuffle them (only once per quiz session)
        all_definitions = [term.get('Definition', 'No definition') for term in matching_terms]
        
        # Shuffle definitions the first time we see this question
        if q_idx_pool not in st.session_state.shuffled_matching_definitions:
            shuffled_definitions = all_definitions.copy()
            random.shuffle(shuffled_definitions)
            st.session_state.shuffled_matching_definitions[q_idx_pool] = shuffled_definitions
        else:
            # Use the already shuffled definitions
            shuffled_definitions = st.session_state.shuffled_matching_definitions[q_idx_pool]
        
        # Create a table-like display with terms on left, dropdown selection on right
        all_terms_matched = True  # Track if all terms have selections
        
        for i, term_data in enumerate(matching_terms):
            term = term_data.get('Term', 'Unknown Term')
            correct_definition = term_data.get('Definition', 'No definition')
            
            cols = st.columns([3, 1, 4])
            with cols[0]:
                st.write(f"**{i+1}. {term}**")
            
            with cols[2]:
                current_selection = st.session_state.matching_answers.get(q_idx_pool, {}).get(i)
                
                # Find the index of the current selection in the shuffled definitions
                try:
                    selected_index = shuffled_definitions.index(current_selection) if current_selection in shuffled_definitions else 0
                except (ValueError, TypeError):
                    selected_index = 0
                
                # Create unique widget key to detect changes
                matching_widget_key = f"matching_{q_idx_pool}_{i}"
                
                # Create the dropdown with shuffled definitions
                selection = st.selectbox(
                    f"Definition for {term}",
                    options=shuffled_definitions,
                    index=selected_index,
                    key=matching_widget_key,
                    label_visibility="collapsed"
                )
                
                # Save this selection from the widget to state
                if q_idx_pool not in st.session_state.matching_answers:
                    st.session_state.matching_answers[q_idx_pool] = {}
                
                st.session_state.matching_answers[q_idx_pool][i] = selection
                
                # Check if this term has been matched
                if not selection:
                    all_terms_matched = False

        # Store the matching answers in the user_answers dictionary
        st.session_state.user_answers[q_idx_pool] = st.session_state.matching_answers.get(q_idx_pool, {})
        
        # Add a verify button for learning mode
        if st.session_state.learning_mode:
            is_verified = st.session_state.verified_matching_questions.get(q_idx_pool, False)
            
            if not is_verified:
                if st.button("Verify Answers", key=f"verify_btn_{q_idx_pool}", use_container_width=True):
                    verify_matching_question(q_idx_pool)
                    st.rerun()
        
    elif q_type == 'Matching':  # Handle individual matching items (should not occur with our fix)
        st.info(f"""
        **Matching Term:**
        Term: **{question_data.get('Term', 'N/A')}**
        Group: **{question_data.get('Group', 'N/A')}**
        Definition: **{question_data.get('Definition', 'N/A')}**

        *(Note: This is part of a matching group. Please see the group question.)*
        """, icon='📝')

    else:
        st.warning(f"Unsupported question type: {q_type}")

    # --- Learning Mode: Automatic Answer Feedback ---
    if st.session_state.learning_mode and has_answer:
        # For regular questions, show feedback immediately
        # For matching questions, only show feedback if verified
        is_matching = q_type == 'MatchingGroup'
        is_verified = st.session_state.verified_matching_questions.get(q_idx_pool, False)
        
        if (not is_matching) or (is_matching and is_verified):
            st.divider()
            st.subheader("Answer Feedback:")
            
            if q_type in ["MCQ", "TF", "FillBlank"]:
                correct_answer = question_data.get('CorrectAnswer')
                is_correct = False
                
                if q_type == "TF":
                    is_correct = (current_answer == correct_answer)
                elif q_type in ["MCQ", "FillBlank"]:
                    is_correct = (str(current_answer).strip().lower() == str(correct_answer).strip().lower())
                
                # Display correctness with appropriate styling
                if is_correct:
                    st.markdown("✅ **Correct!**")
                else:
                    st.markdown("❌ **Incorrect.**")
                    st.markdown(f"Correct answer: **{correct_answer}**")
                
                # Show explanation
                if explanation:
                    st.markdown("**Explanation:**")
                    st.markdown(explanation)
            
            elif q_type == "MatchingGroup" and is_verified:
                matching_terms = question_data.get('MatchingTerms', [])
                user_matching_answers = st.session_state.matching_answers.get(q_idx_pool, {})
                
                st.markdown("**Matching Results:**")
                
                # Display results for each term
                for i, term_data in enumerate(matching_terms):
                    term = term_data.get('Term', 'Unknown Term')
                    correct_definition = term_data.get('Definition', 'No definition')
                    user_definition = user_matching_answers.get(i)
                    
                    if user_definition:
                        is_term_correct = user_definition.strip().lower() == correct_definition.strip().lower()
                        result_icon = "✅" if is_term_correct else "❌"
                        
                        # Display term result
                        st.markdown(f"{result_icon} **{term}**")
                        
                        if not is_term_correct:
                            st.markdown(f"Your match: {user_definition}")
                            st.markdown(f"Correct match: **{correct_definition}**")
                        
                        # Show explanation if available for the term
                        term_explanation = term_data.get('Explanation', '')
                        if term_explanation:
                            with st.expander(f"Explanation for {term}"):
                                st.markdown(term_explanation)

    st.divider()

    # --- Navigation Buttons ---
    col1, col2, col3 = st.columns([1, 8, 1])
    with col1:
        if q_idx_pool > 0:
            prev_button_key = f"prev_btn_{q_idx_pool}"
            if st.button("⬅️ Previous", key=prev_button_key, use_container_width=True):
                st.session_state.current_question_index = q_idx_pool - 1
                st.rerun()
    
    with col3:
        if q_idx_pool < len(st.session_state.quiz_pool) - 1:
            next_button_key = f"next_btn_{q_idx_pool}"
            if st.button("Next ➡️", key=next_button_key, use_container_width=True):
                st.session_state.current_question_index = q_idx_pool + 1
                st.rerun()
        else:
            review_button_key = f"review_btn_{q_idx_pool}"
            if st.button("Review/Submit", key=review_button_key, type="primary", use_container_width=True):
                submit_quiz()
                st.rerun()

def reset_quiz():
    """Resets the quiz state to allow starting a new quiz while keeping the user logged in."""
    # Keep login state but reset quiz and setup
    st.session_state.setup_complete = False
    st.session_state.quiz_pool = []
    st.session_state.current_question_index = 0
    st.session_state.user_answers = {}
    st.session_state.flagged_questions = {}
    st.session_state.submitted = False
    st.session_state.shuffled_mcq_options = {}
    st.session_state.matching_answers = {}
    st.session_state.shuffled_matching_definitions = {}  # Reset the shuffled definitions
    st.session_state.verified_matching_questions = {}  # Reset verified matching questions
    # Reset selected counts too
    st.session_state.selected_counts = {
        q_type: 0 for q_type in st.session_state.available_counts
    }
    st.session_state.selected_matching_groups = []
    # Keep learning mode setting for next quiz

def display_results_quiz():
    st.title("Quiz Results")

    score = 0
    total_questions_in_pool = len(st.session_state.quiz_pool)
    interactive_question_count = 0  # Count only questions that were interactively answerable
    answered_count = 0
    matching_term_count = 0  # Count of individual matching terms
    matching_correct_count = 0  # Count of correctly matched terms

    # Calculate score
    for i, q_data in enumerate(st.session_state.quiz_pool):
        user_answer = st.session_state.user_answers.get(i)
        q_type = q_data.get('Type')

        # Handle different question types for scoring
        if q_type in ["MCQ", "TF", "FillBlank"]:
            correct_answer = q_data.get('CorrectAnswer')
            interactive_question_count += 1
            if user_answer is not None:
                answered_count += 1
                is_correct = False
                if q_type == "TF": 
                    is_correct = (user_answer == correct_answer)
                elif q_type in ["MCQ", "FillBlank"]: 
                    is_correct = (str(user_answer).strip().lower() == str(correct_answer).strip().lower())

                if is_correct: 
                    score += 1
        
        elif q_type == "MatchingGroup":
            # For matching groups, each term is counted separately
            matching_terms = q_data.get('MatchingTerms', [])
            group_term_count = len(matching_terms)
            matching_term_count += group_term_count
            
            # Count answered terms
            if user_answer:  # Dictionary of {term_idx: selected_definition}
                answered_count += len(user_answer)
                
                # Check correct matches
                for term_idx, term_data in enumerate(matching_terms):
                    if term_idx in user_answer:
                        selected_definition = user_answer[term_idx]
                        correct_definition = term_data.get('Definition', '')
                        
                        if selected_definition.strip().lower() == correct_definition.strip().lower():
                            matching_correct_count += 1
                            score += 1

    # Total interactive question count includes individual terms in matching groups
    total_interactive = interactive_question_count + matching_term_count
    
    # Display score based on interactive questions
    if total_interactive > 0:
        st.subheader(f"Your Score: {score} out of {total_interactive} ({score/total_interactive:.1%})")
        st.progress(score / total_interactive)
    else:
        st.subheader("No scorable questions were included in the quiz.")

    st.write(f"Answered: {answered_count} out of {total_interactive} interactive questions/terms.")
    st.write(f"Total items in quiz: {total_questions_in_pool} (containing {total_interactive} scorable items)")
    st.divider()

    st.header("Review Answers")

    for i, q_data in enumerate(st.session_state.quiz_pool):
        q_type = q_data.get('Type', 'N/A')
        question_text = q_data.get('Question', 'N/A')
        user_answer = st.session_state.user_answers.get(i)
        explanation = q_data.get('Explanation', 'No explanation provided.')

        st.markdown(f"**Question {i+1} ({q_type}): {question_text}**")
        
        if q_type in ["MCQ", "TF", "FillBlank"]:
            correct_answer = q_data.get('CorrectAnswer', 'N/A')
            
            # Determine correctness for display
            is_correct = None
            if user_answer is not None:
                if q_type == "TF": 
                    is_correct = (user_answer == correct_answer)
                else: 
                    is_correct = (str(user_answer).strip().lower() == str(correct_answer).strip().lower())

            # Setup display elements
            result_color = "gray"
            result_icon = ""

            if is_correct is True: 
                result_color, result_icon = "green", "✅ Correct"
            elif is_correct is False: 
                result_color, result_icon = "red", "❌ Incorrect"
            else: 
                result_color, result_icon = "orange", "❓ Not Answered"

            # Display user's answer vs correct answer
            if user_answer is not None:
                st.markdown(f"Your Answer: <span style='color:{result_color};'>{str(user_answer)}</span>", unsafe_allow_html=True)
                if not is_correct:
                    correct_display = str(correct_answer)
                    st.markdown(f"Correct Answer: <span style='color:green;'>{correct_display}</span>", unsafe_allow_html=True)
            else:
                st.markdown("Your Answer: <span style='color:orange;'>Not Answered</span>", unsafe_allow_html=True)
                correct_display = str(correct_answer)
                st.markdown(f"Correct Answer: <span style='color:green;'>{correct_display}</span>", unsafe_allow_html=True)
            
            # Show explanation in an expander
            if explanation:
                with st.expander("Show Explanation"):
                    st.write(explanation)
            
            # Show result icon at the end
            st.markdown(f"*{result_icon}*")
            
        elif q_type == "MatchingGroup":
            # Display matching group results
            matching_terms = q_data.get('MatchingTerms', [])
            group_name = q_data.get('Group', 'Unknown Group')
            
            st.write(f"**Matching Group: {group_name}**")
            
            # Create a table to display results
            if matching_terms:
                # Add a header for the results table
                col_headers = st.columns([3, 4, 3])
                with col_headers[0]:
                    st.write("**Term**")
                with col_headers[1]:
                    st.write("**Your Match**")
                with col_headers[2]:
                    st.write("**Correct Match**")
                
                # Display each term and result
                for term_idx, term_data in enumerate(matching_terms):
                    term = term_data.get('Term', 'Unknown')
                    correct_definition = term_data.get('Definition', 'No definition')
                    
                    # Get user's selection for this term
                    user_selection = user_answer.get(term_idx, "Not answered") if user_answer else "Not answered"
                    
                    # Determine if the match was correct
                    is_match_correct = user_selection.strip().lower() == correct_definition.strip().lower() if user_selection != "Not answered" else False
                    
                    # Display the term and matches
                    cols = st.columns([3, 4, 3])
                    with cols[0]:
                        st.write(f"{term_idx+1}. {term}")
                    
                    with cols[1]:
                        if user_selection == "Not answered":
                            st.markdown("<span style='color:orange;'>Not answered</span>", unsafe_allow_html=True)
                        elif is_match_correct:
                            st.markdown(f"<span style='color:green;'>{user_selection} ✅</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<span style='color:red;'>{user_selection} ❌</span>", unsafe_allow_html=True)
                    
                    with cols[2]:
                        st.write(correct_definition)
            
            else:
                st.write("No terms available for this matching group.")
        
        elif q_type == "Matching":  # Individual matching item (shouldn't appear)
            st.info(f"""
            Term: **{q_data.get('Term', 'N/A')}**
            Group: **{q_data.get('Group', 'N/A')}**
            Correct Definition: **{q_data.get('Definition', 'N/A')}**
            """)
        
        st.divider()
        
    # Add a button to take another quiz
    if st.button("Take Another Quiz", type="primary", use_container_width=True):
        reset_quiz()
        st.rerun()

# --- Main App Logic ---
init_session_state()

if not st.session_state.questions_by_type:
    st.error("Question data could not be loaded. Please check the CSV file format.")
elif not st.session_state.setup_complete:
    display_setup_screen()
elif st.session_state.submitted:
    display_results_quiz()
else:
    if not st.session_state.quiz_pool:
        st.error("Quiz pool is empty. Cannot start quiz.")
        # Add button to go back to setup
        if st.button("Return to Setup"):
            st.session_state.setup_complete = False
            st.rerun()
    else:
        display_sidebar_quiz()
        display_question_quiz(st.session_state.current_question_index)