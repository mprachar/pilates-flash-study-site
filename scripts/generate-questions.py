#!/usr/bin/env python3
"""
Generate questions.json from raw extracted data.
Adds plausible wrong answers based on anatomy/kinesiology domain knowledge.
"""

import json
import random
import shutil
import os

# Load raw data
with open('data/questions-raw.json') as f:
    raw = json.load(f)

# ── DISTRACTOR POOLS ──
# Organized by topic area for plausible wrong answers

JOINT_TYPES = {
    'connections': ['Fibrous', 'Cartilaginous', 'Synovial', 'Ligamentous', 'Tendinous'],
    'mobility': ['Diarthrotic', 'Synarthrotic', 'Amphiarthrotic'],
    'joints': ['Ball-and-socket', 'Hinge', 'Pivot', 'Saddle', 'Condyloid', 'Gliding', 'Planar'],
}

DIRECTIONS = {
    'relative': ['Proximal', 'Distal', 'Medial', 'Lateral', 'Superior', 'Inferior', 'Anterior', 'Posterior',
                 'Superficial', 'Deep'],
    'descriptions': [
        'Toward the midline of the body', 'Away from the midline of the body',
        'Closer to the point of attachment', 'Farther from the point of attachment',
        'Toward the front of the body', 'Toward the back of the body',
        'Above or higher', 'Below or lower',
        'Closer to the surface', 'Farther from the surface',
    ],
}

MOVEMENTS = {
    'actions': ['Flexion', 'Extension', 'Abduction', 'Adduction', 'Rotation', 'Circumduction',
                'Pronation', 'Supination', 'Dorsiflexion', 'Plantarflexion',
                'Inversion', 'Eversion', 'Protraction', 'Retraction', 'Elevation', 'Depression',
                'Lateral flexion', 'Hyperextension'],
    'planes': ['Sagittal plane', 'Frontal (coronal) plane', 'Transverse (horizontal) plane', 'Midsagittal plane'],
    'descriptions': [
        'Sideways movement toward the midline of the body',
        'Sideways movement away from the midline of the body',
        'Bending movement that decreases the angle between parts',
        'Straightening movement that increases the angle between parts',
        'Turning a bone around its own axis',
        'Circular movement combining flexion, extension, abduction, and adduction',
        'Forward and backward movement',
        'Movement toward or away from the midline',
        'Turning the palm face down',
        'Turning the palm face up',
    ],
}

CONTRACTION_TYPES = {
    'types': ['Isometric', 'Isotonic concentric', 'Isotonic eccentric', 'Isokinetic'],
    'descriptions': [
        'Contracts without getting shorter or longer',
        'Muscle shortens as it overcomes resistance',
        'Muscle lengthens while maintaining tension',
        'Muscle contracts at a constant speed',
        'Muscle generates force without movement',
        'Muscle lengthens as it resists a load',
    ],
    'terms': ['Agonist', 'Antagonist', 'Synergist', 'Stabilizer', 'Prime mover',
              'Fascicle', 'Myofibril', 'Sarcomere', 'Tendon', 'Aponeurosis',
              'Origin', 'Insertion', 'Muscle belly'],
}

FOREARM_MUSCLES = {
    'muscles': ['Brachialis', 'Biceps brachii', 'Brachioradialis', 'Triceps brachii',
                'Pronator teres', 'Supinator', 'Anconeus', 'Pronator quadratus'],
    'landmarks': ['Ulnar tuberosity', 'Radial tuberosity', 'Medial epicondyle of humerus',
                  'Lateral epicondyle of humerus', 'Olecranon process', 'Coronoid process of ulna',
                  'Coracoid process', 'Deltoid tuberosity', 'Bicipital groove',
                  'Lateral supracondylar ridge', 'Styloid process of radius'],
    'actions': ['Flexion of the elbow', 'Extension of the elbow', 'Pronation of the forearm',
                'Supination of the forearm', 'Flexion of the shoulder'],
}

SCAPULA_MUSCLES = {
    'muscles': ['Pectoralis minor', 'Rhomboid major', 'Rhomboid minor', 'Serratus anterior',
                'Levator scapulae', 'Trapezius (upper)', 'Trapezius (middle)', 'Trapezius (lower)',
                'Subclavius'],
    'landmarks': ['Medial border of the scapula', 'Superior angle of the scapula',
                  'Inferior angle of the scapula', 'Spine of the scapula',
                  'Coracoid process', 'Acromion process', 'Ribs 3-5', 'Ribs 1-8',
                  'Spinous processes of C7-T5', 'Spinous processes of T1-T12',
                  'Mastoid process', 'Transverse processes of C1-C4',
                  'Nuchal line', 'External occipital protuberance'],
    'actions': ['Protraction of the scapula', 'Retraction of the scapula', 'Elevation of the scapula',
                'Depression of the scapula', 'Downward rotation of the scapula',
                'Upward rotation of the scapula', 'Anterior tilt of the scapula'],
}

SHOULDER_MUSCLES = {
    'muscles': ['Anterior deltoid', 'Middle deltoid', 'Posterior deltoid',
                'Latissimus dorsi', 'Pectoralis major', 'Teres major', 'Teres minor',
                'Supraspinatus', 'Infraspinatus', 'Subscapularis', 'Coracobrachialis'],
    'landmarks': ['Lateral third of the clavicle', 'Acromion process', 'Spine of the scapula',
                  'Deltoid tuberosity', 'Greater tubercle of humerus', 'Lesser tubercle of humerus',
                  'Bicipital groove', 'Thoracolumbar fascia', 'Iliac crest',
                  'Supraspinous fossa', 'Infraspinous fossa', 'Subscapular fossa',
                  'Crest of lesser tubercle', 'Intertubercular groove'],
    'actions': ['Flexion of the humerus', 'Extension of the humerus',
                'Abduction of the humerus', 'Adduction of the humerus',
                'Internal rotation of the humerus', 'External rotation of the humerus',
                'Horizontal adduction', 'Horizontal abduction'],
}

KNEE_MUSCLES = {
    'muscles': ['Rectus femoris', 'Vastus lateralis', 'Vastus medialis', 'Vastus intermedius',
                'Biceps femoris', 'Semitendinosus', 'Semimembranosus',
                'Sartorius', 'Gracilis', 'Popliteus', 'Gastrocnemius'],
    'landmarks': ['Tibial tuberosity', 'Head of fibula', 'Ischial tuberosity',
                  'AIIS (Anterior inferior iliac spine)', 'Linea aspera',
                  'Medial condyle of tibia', 'Lateral condyle of tibia',
                  'Patella', 'Patellar tendon', 'Pes anserinus',
                  'Greater trochanter', 'Intertrochanteric line'],
    'actions': ['Flexion of the knee', 'Extension of the knee',
                'Flexion of the hip', 'Extension of the hip',
                'Internal rotation of the knee', 'External rotation of the knee',
                'Internal rotation of the hip', 'External rotation of the hip'],
}

ANKLE_MUSCLES = {
    'muscles': ['Gastrocnemius', 'Gastrocnemius (medial head)', 'Gastrocnemius (lateral head)',
                'Soleus', 'Tibialis anterior', 'Tibialis posterior',
                'Peroneus longus', 'Peroneus brevis', 'Peroneus tertius',
                'Extensor digitorum longus', 'Flexor digitorum longus'],
    'landmarks': ['Calcaneus (via Achilles tendon)', 'First metatarsal', 'Fifth metatarsal',
                  'Medial cuneiform', 'Lateral condyle of femur', 'Medial condyle of femur',
                  'Head of fibula', 'Lateral malleolus', 'Medial malleolus',
                  'Soleal line of tibia', 'Proximal tibia'],
    'actions': ['Plantarflexion of the ankle', 'Dorsiflexion of the ankle',
                'Inversion of the foot', 'Eversion of the foot',
                'Flexion of the knee', 'Extension of the toes',
                'Flexion of the toes'],
}

HIP_MUSCLES = {
    'muscles': ['Gluteus maximus', 'Gluteus medius', 'Gluteus minimus',
                'Piriformis', 'Psoas major', 'Iliacus', 'Tensor fasciae latae (TFL)',
                'Adductor magnus', 'Adductor longus', 'Adductor brevis',
                'Pectineus', 'Gracilis', 'Sartorius',
                'Obturator internus', 'Obturator externus',
                'Gemellus superior', 'Gemellus inferior', 'Quadratus femoris',
                'Rectus femoris'],
    'landmarks': ['Acetabulum', 'Greater trochanter', 'Lesser trochanter',
                  'Iliac crest', 'ASIS (Anterior superior iliac spine)',
                  'AIIS (Anterior inferior iliac spine)',
                  'Ischial tuberosity', 'Ischium', 'Pubic symphysis',
                  'Linea aspera', 'Gluteal tuberosity', 'IT band',
                  'Sacrum', 'Intertrochanteric crest', 'Iliac fossa',
                  'Trochanteric fossa', 'Obturator foramen'],
    'actions': ['Flexion of the hip', 'Extension of the hip',
                'Abduction of the hip', 'Adduction of the hip',
                'Internal rotation of the hip', 'External rotation of the hip',
                'Lateral rotation of the hip'],
}

NECK_MUSCLES = {
    'muscles': ['Sternocleidomastoid', 'Anterior scalene', 'Middle scalene', 'Posterior scalene',
                'Splenius capitis', 'Splenius cervicis', 'Semispinalis capitis',
                'Longus capitis', 'Longus colli', 'Levator scapulae', 'Upper trapezius'],
    'landmarks': ['Mastoid process', 'Manubrium of the sternum', 'Medial clavicle',
                  'Transverse processes of C1-C4', 'Transverse processes of C3-C6',
                  'Spinous processes of C7-T3', 'First rib', 'Second rib',
                  'Nuchal line', 'Temporal bone', 'Occipital bone',
                  'Superior nuchal line', 'External occipital protuberance'],
    'actions': ['Flexion of the neck', 'Extension of the neck',
                'Lateral flexion of the neck', 'Rotation to the same side',
                'Rotation to the opposite side', 'Elevation of the first rib',
                'Bilateral: flexion of the neck', 'Unilateral: lateral flexion'],
}

TRUNK_MUSCLES = {
    'muscles': ['Rectus abdominis', 'External obliques', 'Internal obliques',
                'Transversus abdominis', 'Quadratus lumborum',
                'Erector spinae (iliocostalis)', 'Erector spinae (longissimus)',
                'Erector spinae (spinalis)', 'Multifidus'],
    'landmarks': ['Pubic symphysis', 'Xiphoid process', 'Iliac crest',
                  'Inguinal ligament', 'Linea alba', 'Thoracolumbar fascia',
                  'Lower 8 ribs', 'Ribs 5-12', 'Ribs 10-12',
                  'Twelfth rib', 'Transverse processes of L1-L4',
                  'Spinous processes', 'Costal cartilages'],
    'actions': ['Flexion of the trunk', 'Extension of the trunk',
                'Lateral flexion of the trunk', 'Rotation of the trunk to the same side',
                'Rotation of the trunk to the opposite side',
                'Compression of abdominal contents', 'Posterior pelvic tilt',
                'Anterior pelvic tilt', 'Elevation of the pelvis (hip hiking)',
                'Stabilization of the lumbar spine'],
}

BREATHING_MUSCLES = {
    'muscles': ['Diaphragm', 'External intercostals', 'Internal intercostals',
                'Scalenes', 'Sternocleidomastoid', 'Pectoralis minor',
                'Serratus anterior', 'Abdominals (forced expiration)'],
    'landmarks': ['Vertebrae L1-L3', 'Xiphoid process', 'Lower 6 costal cartilages',
                  'Central tendon', 'Lower 6 ribs', 'Upper 6 ribs',
                  'Sternum', 'Costal margin'],
    'actions': ['Inspiration (inhalation)', 'Expiration (exhalation)',
                'Forced inspiration', 'Forced expiration',
                'Elevates the ribs', 'Depresses the ribs',
                'Increases thoracic volume', 'Decreases thoracic volume',
                'Flattens during contraction', 'Dome-shaped at rest'],
}

# Map section IDs to distractor pools
SECTION_POOLS = {
    'general-anatomy': {**JOINT_TYPES, **DIRECTIONS, **MOVEMENTS},
    'muscle-contractions': CONTRACTION_TYPES,
    'forearm': FOREARM_MUSCLES,
    'scapula': SCAPULA_MUSCLES,
    'shoulder': SHOULDER_MUSCLES,
    'knee': KNEE_MUSCLES,
    'ankle': ANKLE_MUSCLES,
    'hip': HIP_MUSCLES,
    'neck': NECK_MUSCLES,
    'trunk': TRUNK_MUSCLES,
    'breathing': BREATHING_MUSCLES,
}

# Collect all correct answers per section for cross-question distractors
section_answers = {}
for q in raw['questions']:
    sec = q['section']
    if sec not in section_answers:
        section_answers[sec] = set()
    for ans in q['answers']:
        section_answers[sec].add(ans)


def classify_answer(answer, pool):
    """Determine which pool category an answer belongs to (muscles, landmarks, actions, etc.)."""
    answer_lower = answer.lower().strip()
    for category, values in pool.items():
        for v in values:
            if v.lower().strip() == answer_lower or answer_lower in v.lower() or v.lower() in answer_lower:
                return category
    # Heuristic classification
    action_words = ['flexion', 'extension', 'abduction', 'adduction', 'rotation', 'movement',
                    'plantarflexion', 'dorsiflexion', 'inversion', 'eversion', 'protraction',
                    'retraction', 'elevation', 'depression', 'lateral flex', 'stabiliz']
    landmark_words = ['process', 'tuberosity', 'condyle', 'fossa', 'crest', 'spine of',
                      'border', 'angle', 'rib', 'vertebr', 'iliac', 'ischial', 'pubic',
                      'trochanter', 'epicondyle', 'malleolus', 'metatarsal', 'cuneiform',
                      'manubrium', 'xiphoid', 'linea', 'nuchal', 'occipital', 'calcaneus',
                      'origin of', 'insertion of', 'bony landmark']
    muscle_words = ['muscle', 'deltoid', 'biceps', 'triceps', 'brachialis', 'pectoralis',
                    'latissimus', 'trapezius', 'rhomboid', 'serratus', 'levator',
                    'gastrocnemius', 'soleus', 'tibialis', 'peroneus', 'gluteus',
                    'piriformis', 'psoas', 'iliacus', 'rectus', 'vastus', 'oblique',
                    'sternocleidomastoid', 'scalene', 'splenius', 'diaphragm',
                    'intercostal', 'adductor', 'sartorius', 'gracilis', 'quadratus',
                    'erector', 'transversus', 'obturator', 'gemellus', 'subscapularis',
                    'supraspinatus', 'infraspinatus', 'coracobrachialis', 'anconeus',
                    'supinator', 'pronator', 'popliteus', 'semimembranosus', 'semitendinosus',
                    'teres', 'multifidus', 'tensor']

    al = answer_lower
    if any(w in al for w in action_words):
        return 'actions'
    if any(w in al for w in landmark_words):
        return 'landmarks'
    if any(w in al for w in muscle_words):
        return 'muscles'
    return None


def get_distractors(question, correct_answer, section_id, all_correct_in_section):
    """Generate 3 plausible wrong answers for a question, matched by category."""
    pool = SECTION_POOLS.get(section_id, {})
    correct_lower = correct_answer.lower().strip()

    # Classify the correct answer
    answer_category = classify_answer(correct_answer, pool)

    # Strategy 1: Same-category pool values (most plausible)
    same_category = []
    if answer_category and answer_category in pool:
        same_category = [v for v in pool[answer_category] if v.lower().strip() != correct_lower]

    # Strategy 2: Same-category answers from the section
    same_section_same_cat = []
    same_section_any = []
    for a in all_correct_in_section:
        if a.lower().strip() == correct_lower:
            continue
        a_cat = classify_answer(a, pool)
        if a_cat == answer_category and answer_category is not None:
            same_section_same_cat.append(a)
        else:
            same_section_any.append(a)

    # Build candidate list: prioritize same-category, then same-section-same-category, then others
    candidates = []
    seen = {correct_lower}

    for source in [same_category, same_section_same_cat, same_section_any]:
        random.shuffle(source)
        for c in source:
            cl = c.lower().strip()
            if cl not in seen:
                candidates.append(c)
                seen.add(cl)

    # If still not enough, use all pool values
    if len(candidates) < 3:
        all_pool = []
        for values in pool.values():
            all_pool.extend(values)
        random.shuffle(all_pool)
        for c in all_pool:
            cl = c.lower().strip()
            if cl not in seen:
                candidates.append(c)
                seen.add(cl)

    return candidates[:3]


def build_explanation(question_text, correct_answer, q_type):
    """Build a brief explanation."""
    if q_type == 'tf':
        if correct_answer.lower() == 'true':
            return f"This statement is correct."
        else:
            return f"This statement is false."

    return f"The correct answer is: {correct_answer}"


# ── BUILD OUTPUT ──
output = {
    'version': 1,
    'sections': raw['sections'],
    'questions': [],
}

for q in raw['questions']:
    correct = q['answers'][0] if q['answers'] else ''
    if not correct:
        continue

    # For multi-answer questions, join them
    if len(q['answers']) > 1 and q['type'] == 'multi':
        correct = ', '.join(q['answers'])

    section_correct = list(section_answers.get(q['section'], set()))
    distractors = get_distractors(q['text'], correct, q['section'], section_correct)

    # For T/F questions, use True/False as answers
    if q['type'] == 'tf':
        if correct.lower() == 'true':
            distractors = ['False']
        else:
            distractors = ['True']

    # Make sure we have at least 3 distractors (or 1 for T/F)
    min_distractors = 1 if q['type'] == 'tf' else 3
    if len(distractors) < min_distractors:
        # Pad with generic plausible answers
        padding = ['None of the above', 'All of the above', 'Cannot be determined']
        for p in padding:
            if len(distractors) >= min_distractors:
                break
            if p.lower() != correct.lower():
                distractors.append(p)

    question_obj = {
        'id': q['id'],
        'section': q['section'],
        'question': q['text'],
        'correctAnswer': correct,
        'wrongAnswers': distractors[:min_distractors if q['type'] == 'tf' else 3],
        'explanation': build_explanation(q['text'], correct, q['type']),
        'image': q['image'],
    }
    output['questions'].append(question_obj)

# Move images to images/ dir
src_img_dir = 'data/images'
dst_img_dir = 'images'
os.makedirs(dst_img_dir, exist_ok=True)
for q in output['questions']:
    if q['image']:
        src = os.path.join(src_img_dir, q['image'])
        dst = os.path.join(dst_img_dir, q['image'])
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)

# Save
with open('data/questions.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"Generated {len(output['questions'])} questions")
print(f"  T/F: {sum(1 for q in output['questions'] if len(q['wrongAnswers']) == 1)}")
print(f"  Multiple choice: {sum(1 for q in output['questions'] if len(q['wrongAnswers']) == 3)}")
print(f"  With images: {sum(1 for q in output['questions'] if q['image'])}")

# Verify distractor quality
bad = 0
for q in output['questions']:
    if len(q['wrongAnswers']) < (1 if q['wrongAnswers'] == ['True'] or q['wrongAnswers'] == ['False'] else 3):
        bad += 1
        print(f"  WARNING: Q{q['id']} has only {len(q['wrongAnswers'])} distractors")
if bad == 0:
    print("All questions have sufficient distractors!")
