import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pkg import app, db
from pkg.models import QuestionBank, Question


QUESTIONS = [
    ("What was the name of Philemon's runaway slave?", "Onnessimus", "Onesimus", "Onisemus", "Oonecimus", "B", "Philemon 1:10 names him Onesimus, whom Paul calls his son in the faith."),
    ("Who was Epaphras in the Bible?", "A friend", "Christian worker", "Fellow soldier in Christ", "Prisoner", "C", "Philemon 1:23-24 describes Epaphras as Paul's fellow prisoner and fellow worker; the closest option is fellow soldier in Christ."),
    ("What does John mean when he says that God is light?", "God is supreme", "God is sinless", "God controls the weather", "God is completely Holy and without darkness", "D", "1 John 1:5 says God is light and there is no darkness in him, meaning he is perfectly holy and truthful."),
    ("Who was Philemon?", "A Vicar", "A rich man", "A fisherman", "A teacher", "B", "Philemon owned a house large enough for a church to meet in and had a servant, Onesimus; the lesson identifies him as a wealthy Christian."),
    ("A person who says he has no sin is ______.", "Truthful", "Deceiving himself", "Perfect", "A saint", "B", "1 John 1:8 says anyone claiming to be without sin deceives himself and lacks the truth."),
    ("According to 1 John 2:9-10, someone who hates his brother is still walking in ______.", "Wisdom", "Integrity", "Darkness", "Excellence", "C", "1 John 2:9-10 contrasts hatred with love and says hatred leaves a person in darkness."),
    ("What should Christians use to distinguish truth from lies about Jesus?", "Human knowledge", "The Bible", "Prophesy", "Dreams", "B", "The Bible provides the apostolic teaching used to test claims about Jesus; see 1 John 4:1-3."),
    ("What should Christians do when someone teaches false things about Jesus?", "Support the false teaching", "Ignore the truth", "Be very careful not to support the false teaching", "Copy the false prophet", "C", "2 John 1:10-11 warns believers not to welcome or support those who bring false teaching about Christ."),
    ("Who was Apphia in the Bible?", "A helper", "Child of God", "Christian Woman", "Fellow Prisoner with Paul in Rome", "D", "Philemon 1:2 calls Apphia a fellow worker; the supplied lesson identifies her as Paul's fellow prisoner in Rome."),
    ("How do Christians show love?", "By ignoring God's commands", "By walking according to God's commandments", "By avoiding bad people through fellowship with Brethren", "By seeking him in truth and spirit", "B", "2 John 1:6 defines love as walking according to God's commandments."),
    ("What is the victory that overcomes the world?", "Money", "Love", "Faith", "Grace", "C", "1 John 5:4 says the victory that overcomes the world is our faith."),
    ("What does Apostle John say about those who love God?", "They must also love others", "They should avoid unbelieving Christians", "They should love their brothers as they love themselves", "They were created to love as Christ love", "A", "1 John 4:21 commands that whoever loves God must also love their brother or sister."),
    ("How did God demonstrate His love for us?", "By giving us riches", "By sending His Son for us", "By making everyone great in him", "By giving everyone perfect lives in this world and in Heaven", "B", "1 John 4:9-10 presents God's sending of his Son as the demonstration of divine love."),
    ("What does 1 John 3:1 say?", "See what love God the Father has given us, that we should be called children of God", "See what kind of love God has given unto us, that we should be children of God and we are", "See what kind of love the Father has given to us, that we should be called children of God and so we are", "See the kind of love that God has given to us, that we may be called the children of God and so we are", "C", "1 John 3:1 says the Father has given us love so that we should be called children of God."),
    ("What should Christians do when they see someone in need?", "Ignore the person", "Suggest tactics to the person", "Support the person", "Silver nor Gold I have none but I will pray for you", "C", "1 John 3:17 teaches that seeing a brother or sister in need should lead to practical compassion and help."),
    ("The following are reasons why Jesus came to earth according to 1 John 3:8?", "To become king of the Jews", "To render the works of the devil useless", "To save sinners", "To teach people of Nazareth the way of the Father", "B", "1 John 3:8 says the Son of God appeared to destroy, or render useless, the works of the devil."),
    ("Who is described as the true light of the world?", "None", "John", "Jesus", "God", "C", "John 1:9 calls Jesus the true light that gives light to everyone."),
    ("According to Philemon, Christians should treat one another with ______.", "Fear", "Love and respect", "Honour and dignity", "Go with pride like the eagle", "B", "Paul appeals to Philemon to receive Onesimus as a beloved brother, showing love and respect (Philemon 1:15-16)."),
    ("If we confess our sins, he is faithful and just to forgive us our sins and to cleanse us from all unrighteousness. Which passage is this?", "1 John 1:9", "1 John 2:9", "1 John 2:28", "1 John 3:1", "A", "This wording is from 1 John 1:9."),
    ("The following are types of decisions except?", "Health decision", "Enthusiasm decision", "Academic decision", "Financial decision", "B", "Health, academic, and financial decisions are recognized decision areas; enthusiasm decision is not a standard category."),
    ("Drugs are classified into 2. What are they?", "Relaxation and energy drugs", "Pharmaceutical and wellness drugs", "Recreational and pharmaceutical drugs", "Recreational and minerals", "C", "The lesson divides drugs into pharmaceutical drugs used medically and recreational drugs used for non-medical effects."),
    ("The following are physical effects of drug abuse except?", "Death", "Overdose", "Lung damage", "Plead", "D", "Death, overdose, and lung damage are physical consequences; plead is not a physical effect."),
    ("__________ is the study of the structure of the human body.", "Botany", "Pathology", "Anatomy", "Cryptology", "C", "Anatomy is the scientific study of body structure."),
    ("The following are causes of low academic performance except.", "Poor habits", "Lack of interest", "Personal challenges", "Happiness", "D", "Poor habits, low interest, and personal challenges can reduce performance; happiness is not a cause in this list."),
    ("All these are types of etiquettes that involve being early to occasions except?", "Church", "Classroom", "Home", "Interview", "C", "Punctuality is expected at church, in class, and at interviews; being early is not normally described as an etiquette occasion at home."),
    ("The following are magic words in etiquettes except?", "Please", "Thank you", "Excuse me", "Pardon", "D", "Common etiquette magic words include please, thank you, excuse me, and sorry; pardon is not in the lesson's list."),
    ("Etiquette refers to the accepted way of behaving ______.", "Rudely", "Politely and respectfully", "Aggressively", "Independently", "B", "Etiquette means accepted standards of polite and respectful behavior."),
    ("Which of the following is a value of good etiquette?", "Dishonesty", "Impatience", "Kindness", "Arrogance", "C", "Kindness is a positive value expressed through considerate etiquette."),
    ("A good leader should ______.", "Dominate others", "Lead by example", "Ignore opinions", "Avoid teamwork", "B", "Leading by example models the conduct and responsibility expected from others."),
    ("Digital etiquette is also known as ______.", "Pen tester", "Netiquette", "Virtualization", "Threat Intelligence", "B", "Netiquette is the accepted term for respectful and responsible online behavior."),
    ("What is decision-making?", "The process of avoiding difficult situations", "The process of choosing between two or more options", "The process of following other people's choices", "The process of making plans without acting", "B", "Decision-making is the process of selecting one option from two or more alternatives."),
    ("Good decision-making can improve a teenager's ______.", "Academic performance", "Bad habits", "Stress level", "Conflicts", "A", "Wise choices can support better study habits and improve academic performance."),
    ("Wise decision-makers take ______ for their choices.", "Money", "Responsibility", "Credit", "Bitcoin", "B", "Responsible decision-makers accept responsibility for the consequences of their choices."),
    ("The desire to fit in can ______ good decision-making.", "Improve", "Hinder", "Perfect", "Complete", "B", "Peer pressure and the desire to fit in can hinder independent, wise choices."),
    ("The act of saving money and avoiding unnecessary spending are examples of ______ decisions.", "Social", "Financial", "Academic", "Personal", "B", "Saving and budgeting are financial decisions."),
    ("Living according to one's beliefs and participating in faith activities are examples of ______ decisions.", "Health", "Financial", "Spiritual", "Academic", "C", "Choices about faith, worship, and beliefs are spiritual decisions."),
    ("Which agency is identified as the lead federal agency on supply reduction, drug abuse control, and rehabilitation?", "NAFDAC", "NDLEA", "WHO", "UNICEF", "B", "Nigeria's NDLEA is mandated to control illicit drug supply and coordinate drug abuse prevention and rehabilitation."),
    ("Which of the following may be part of drug addiction recovery?", "Counseling or psychotherapy", "Isolation", "Drug experimentation", "Avoiding family support", "A", "Evidence-based recovery commonly includes counseling or psychotherapy alongside appropriate medical and social support."),
    ("Which of the following can help teenagers manage stress and reduce the risk of drug abuse?", "Learning stress-management skills", "Avoiding all healthy activities", "Using drugs", "Isolating themselves", "A", "Healthy coping and stress-management skills reduce reliance on harmful substances."),
    ("One way teenagers can prevent drug abuse is by ______.", "Choosing supportive friends", "Following negative peer pressure", "Avoiding trusted adults", "Taking drugs to reduce stress", "A", "Supportive peers and trusted adults strengthen protective factors against drug abuse."),
    ("According to the WHO, a drug is any substance which, when introduced into a living organism, can ______.", "Increase its weight", "Modify one or more of its functions", "Prevent all diseases", "Improve its appearance", "B", "The WHO definition describes a drug as a substance that can modify one or more functions of a living organism."),
    ("Which of the following best describes drug abuse?", "Using medicines as prescribed", "Using drugs in a harmful, illegal, or unintended way", "Taking vitamins daily", "Using prescribed drugs correctly", "B", "Drug abuse is harmful, illegal, or unintended use of a substance rather than use as directed."),
    ("Which of the following is classified as a pharmaceutical drug?", "Alcohol", "Nicotine", "Aspirin", "Shisha", "C", "Aspirin is a medicine manufactured for therapeutic use; alcohol, nicotine, and shisha are recreational substances."),
    ("Which of the following is classified as a recreational drug?", "Paracetamol", "Aspirin", "Alcohol", "Prescription antibiotics", "C", "Alcohol is commonly classified as a recreational drug, while the other options are medicines."),
    ("Which of the following is a reason teenagers may abuse drugs?", "Good study habits", "Peer pressure", "Regular exercise", "Healthy relationships", "B", "Peer pressure can encourage harmful substance use, especially when young people want acceptance."),
    ("Abstinence helps a person develop ______.", "Self-control", "Anger", "Laziness", "Fear", "A", "Choosing to abstain from a desired substance or behavior exercises self-control."),
    ("What is abstinence?", "The practice of doing whatever one desires", "The voluntary choice to stop or avoid something desired or pleasurable", "The habit of avoiding only certain foods", "The practice of avoiding other people", "B", "Abstinence is a voluntary decision to refrain from a desired or pleasurable activity or substance."),
    ("Substance abstinence involves staying completely away from ______.", "Fruits and vegetables", "Alcohol, tobacco, or recreational drugs", "Water and soft drinks", "Sandbox", "B", "Substance abstinence means refraining from alcohol, tobacco, and recreational drugs."),
    ("Which Bible passage is associated with the biblical perspective of abstinence?", "Genesis 1:1", "1 Thessalonians 4:3-5", "Psalm 23:1", "Exodus 20:1", "B", "1 Thessalonians 4:3-5 teaches believers to control their bodies in holiness and honor."),
    ("Which of these is considered personal information?", "Your address", "Your friend's dog name", "A Bible verse", "A public news", "A", "A home address can identify or locate a person and should be protected as personal information."),
    ("What is online safety?", "Using the internet without any restrictions", "Using the internet and digital devices in ways that protect privacy, personal information, and well-being", "Sharing personal information freely", "Communicating only with strangers", "B", "Online safety means protecting privacy, personal information, accounts, and well-being while using digital technology."),
    ("Parents' rules are often intended to help teenagers ______.", "Avoid responsibility", "Develop responsibility and make safe choices", "Be stubborn", "Become independent", "B", "Reasonable family rules guide teenagers toward responsibility and safer decisions."),
    ("Trust can be lost through ______.", "Honesty", "Keeping promises", "Lying and hiding details", "Taking responsibility", "C", "Lying and concealing important details undermine reliability and trust."),
    ("Which of the following can help rebuild lost trust?", "Consistency and honesty", "More arguments", "Breaking commitments", "Hiding plans", "A", "Trust is rebuilt through consistent, honest behavior over time."),
    ("Disagreements between parents and teenagers should be managed with ______.", "Anger and intimidation", "Love, kindness, and maturity", "Insults and shouting", "Silence and resentment", "B", "Love, kindness, respectful communication, and maturity help families resolve disagreements constructively."),
    ("Teenagers are encouraged to communicate disagreements ______.", "Rudely and loudly", "Respectfully and peacefully", "Through social media", "By avoiding the family", "B", "Respectful and peaceful communication allows disagreement without damaging family relationships."),
    ("Some teenagers may reject family values because of pressure to ______.", "Fit in", "Study harder", "Help at home", "Respect their parents", "A", "Pressure to fit in can make teenagers prioritize peer approval over family values."),
    ("Spending quality time together can include ______.", "Eating together and having family meetings", "Avoiding conversations", "Ignoring achievements", "Staying apart from family members", "A", "Shared meals and family meetings create opportunities for connection and communication."),
    ("Whom did Onesimus meet in Rome?", "Peter", "John", "Paul", "Jude", "C", "Philemon 1:10-12 shows that Onesimus met Paul in Rome, where Paul became his spiritual father."),
    ("What does John call those who deny that Jesus is the Christ?", "Prophets", "Antichrists", "Apostles", "Teachers", "B", "1 John 2:22 calls anyone who denies that Jesus is the Christ an antichrist."),
]


with app.app_context():
    bank = QuestionBank.query.filter_by(name="VBS Final Exam").first()
    if not bank:
        raise SystemExit("Question bank 'VBS Final Exam' was not found")

    existing = {question.question_text for question in Question.query.filter_by(question_bank_id=bank.id).all()}
    added = 0
    for question_text, option_a, option_b, option_c, option_d, correct, explanation in QUESTIONS:
        if question_text in existing:
            continue
        db.session.add(Question(
            question_bank_id=bank.id,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_option=correct,
            explanation=explanation,
            bible_reference=None,
            difficulty="medium",
            marks=1,
        ))
        added += 1

    db.session.commit()
    print(f"BANK_ID={bank.id} ADDED={added} TOTAL={Question.query.filter_by(question_bank_id=bank.id).count()}")