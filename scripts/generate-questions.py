#!/usr/bin/env python3
"""
Generate questions.json from raw extracted data.
Adds plausible wrong answers based on anatomy/kinesiology domain knowledge.
"""

import json
import random
import shutil
import os
import re as re_mod
from zipfile import ZipFile
import xml.etree.ElementTree as ET

# Load raw data
with open('data/questions-raw.json') as f:
    raw = json.load(f)

# ── BUILD CORRECT IMAGE-ROW MAP FROM XLSX XML ──
# openpyxl's _images order doesn't reliably match media file names.
# Parse the drawing XML + rels to get the authoritative mapping.

IMAGE_ROW_MAP = {}  # row -> image filename

with ZipFile('data/quiz-study-guide.xlsx', 'r') as z:
    # Parse relationship IDs -> image filenames
    rid_to_file = {}
    rels_tree = ET.parse(z.open('xl/drawings/_rels/drawing1.xml.rels'))
    for rel in rels_tree.getroot():
        rid = rel.attrib.get('Id', '')
        target = rel.attrib.get('Target', '')
        if 'image' in target.lower():
            rid_to_file[rid] = os.path.basename(target)

    # Parse anchors: row -> rId -> image filename
    nsmap = {
        'xdr': 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    }
    drawing_tree = ET.parse(z.open('xl/drawings/drawing1.xml'))
    anchors = (drawing_tree.getroot().findall('.//xdr:twoCellAnchor', nsmap) +
               drawing_tree.getroot().findall('.//xdr:oneCellAnchor', nsmap))

    for anchor in anchors:
        from_el = anchor.find('xdr:from', nsmap)
        if from_el is None:
            continue
        row = int(from_el.find('xdr:row', nsmap).text)
        blip = anchor.find('.//a:blip', nsmap)
        if blip is None:
            continue
        embed = blip.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed', '')
        if embed in rid_to_file:
            IMAGE_ROW_MAP[row] = rid_to_file[embed]

print(f"Built image map: {len(IMAGE_ROW_MAP)} images")

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

# ── TARGETED DISTRACTORS ──
# Research-backed: when the correct answer matches a key, use these specific distractors
# These are the most commonly confused items per the research
TARGETED_DISTRACTORS = {
    # Joint types
    'fibrous': ['Cartilaginous', 'Synovial', 'Ligamentous'],
    'cartilaginous': ['Fibrous', 'Synovial', 'Ligamentous'],
    'synovial': ['Cartilaginous', 'Fibrous', 'Ligamentous'],
    'diarthrotic': ['Amphiarthrotic', 'Synarthrotic', 'Syndesmotic'],
    'synarthrotic': ['Diarthrotic', 'Amphiarthrotic', 'Syndesmotic'],
    'amphiarthrotic': ['Diarthrotic', 'Synarthrotic', 'Syndesmotic'],
    'diarthrotic, synarthrotic, amphiarthrotic': ['Synarthrotic, diarthrotic, amphiarthrotic', 'Diarthrotic, amphiarthrotic, synarthrotic', 'Amphiarthrotic, diarthrotic, synarthrotic'],
    # Directions
    'distal': ['Proximal', 'Inferior', 'Lateral'],
    'proximal': ['Distal', 'Superior', 'Medial'],
    'medial': ['Lateral', 'Anterior', 'Proximal'],
    'lateral': ['Medial', 'Posterior', 'Distal'],
    'anterior': ['Posterior', 'Ventral', 'Superficial'],
    'posterior': ['Anterior', 'Dorsal', 'Deep'],
    # Movements
    'sideways movement toward the midline of the body': ['Sideways movement away from the midline of the body', 'Circular movement of a limb', 'Bending movement that decreases the angle between parts'],
    'abducting': ['Adducting', 'Extending', 'Rotating'],
    'adducting': ['Abducting', 'Flexing', 'Rotating'],
    'forward and backward movement': ['Sideways movement', 'Rotational movement', 'Circular movement'],
    # Contraction types
    'contracts without getting shorter or longer': ['Muscle shortens as it overcomes resistance', 'Muscle lengthens while maintaining tension', 'Muscle contracts at a constant speed'],
    'isotonic concentric': ['Isotonic eccentric', 'Isometric', 'Isokinetic'],
    'isotonic eccentric': ['Isotonic concentric', 'Isometric', 'Isokinetic'],
    'isometric': ['Isotonic concentric', 'Isotonic eccentric', 'Isokinetic'],
    # Forearm muscles - antagonist/adjacent swaps
    'brachialis': ['Biceps brachii', 'Brachioradialis', 'Triceps brachii'],
    'biceps brachii': ['Brachialis', 'Brachioradialis', 'Coracobrachialis'],
    'brachioradialis': ['Brachialis', 'Biceps brachii', 'Pronator teres'],
    'triceps brachii': ['Biceps brachii', 'Brachialis', 'Anconeus'],
    # Forearm landmarks - adjacent swaps
    'the ulnar tuberosity': ['Radial tuberosity', 'Coronoid process of ulna', 'Olecranon process'],
    'ulnar tuberosity': ['Radial tuberosity', 'Coronoid process of ulna', 'Olecranon process'],
    'radial tuberosity': ['Ulnar tuberosity', 'Coronoid process of ulna', 'Styloid process of radius'],
    'olecranon process': ['Coronoid process of ulna', 'Radial tuberosity', 'Lateral epicondyle'],
    'coronoid process': ['Coracoid process', 'Olecranon process', 'Radial tuberosity'],
    # Scapula muscles
    'pectoralis minor origin': ['Serratus anterior origin', 'Pectoralis major origin', 'Rhomboid minor origin'],
    'medial border of the scapula': ['Lateral border of the scapula', 'Spine of the scapula', 'Superior angle of the scapula'],
    'levator scapulae': ['Rhomboid minor', 'Upper trapezius', 'Serratus anterior'],
    'serratus anterior': ['Rhomboid major', 'Pectoralis minor', 'Levator scapulae'],
    # Shoulder muscles
    'deltoids': ['Latissimus dorsi', 'Pectoralis major', 'Teres major'],
    'anterior deltoids': ['Middle deltoid', 'Posterior deltoid', 'Pectoralis major'],
    'origin of anterior deltoids': ['Origin of middle deltoids', 'Insertion of anterior deltoids', 'Origin of pectoralis major'],
    'latissimus dorsi': ['Teres major', 'Posterior deltoid', 'Infraspinatus'],
    'supraspinatus': ['Infraspinatus', 'Subscapularis', 'Teres minor'],
    'infraspinatus': ['Supraspinatus', 'Teres minor', 'Subscapularis'],
    'subscapularis': ['Infraspinatus', 'Supraspinatus', 'Teres minor'],
    'abduction of the humerus': ['Adduction of the humerus', 'Flexion of the humerus', 'External rotation of the humerus'],
    'greater tubercle of humerus': ['Lesser tubercle of humerus', 'Deltoid tuberosity', 'Intertubercular groove'],
    'lesser tubercle of humerus': ['Greater tubercle of humerus', 'Deltoid tuberosity', 'Bicipital groove'],
    # Knee muscles
    'flexion of the knee and extension of the hip': ['Extension of the knee and flexion of the hip', 'Flexion of the knee and flexion of the hip', 'Extension of the knee and extension of the hip'],
    'tibial tuberosity': ['Head of fibula', 'Medial condyle of tibia', 'Lateral condyle of tibia'],
    'semimembranosus': ['Semitendinosus', 'Biceps femoris', 'Gracilis'],
    'semitendinosus': ['Semimembranosus', 'Biceps femoris', 'Sartorius'],
    'biceps femoris': ['Semitendinosus', 'Semimembranosus', 'Rectus femoris'],
    'rectus femoris': ['Vastus lateralis', 'Vastus medialis', 'Vastus intermedius'],
    # Ankle muscles
    'gastrocnemius': ['Soleus', 'Tibialis posterior', 'Plantaris'],
    'gastrocnemius (lateral head)': ['Gastrocnemius (medial head)', 'Soleus', 'Plantaris'],
    'soleus': ['Gastrocnemius', 'Tibialis posterior', 'Peroneus longus'],
    'tibialis anterior': ['Tibialis posterior', 'Peroneus longus', 'Extensor digitorum longus'],
    'peroneus longus': ['Peroneus brevis', 'Tibialis anterior', 'Tibialis posterior'],
    # Hip muscles
    'adductor magnus': ['Adductor longus', 'Adductor brevis', 'Gracilis'],
    'adductor longus': ['Adductor magnus', 'Adductor brevis', 'Pectineus'],
    'acetabulum': ['Greater trochanter', 'Obturator foramen', 'Iliac fossa'],
    'gluteus maximus': ['Gluteus medius', 'Gluteus minimus', 'Piriformis'],
    'gluteus medius': ['Gluteus minimus', 'Gluteus maximus', 'Tensor fasciae latae'],
    'piriformis': ['Obturator internus', 'Gemellus superior', 'Quadratus femoris'],
    'psoas major': ['Iliacus', 'Rectus femoris', 'Tensor fasciae latae'],
    'iliacus': ['Psoas major', 'Rectus femoris', 'Pectineus'],
    'tensor fasciae latae': ['Gluteus medius', 'Sartorius', 'Rectus femoris'],
    'greater trochanter': ['Lesser trochanter', 'Intertrochanteric crest', 'Gluteal tuberosity'],
    'lesser trochanter': ['Greater trochanter', 'Intertrochanteric line', 'Linea aspera'],
    'ischial tuberosity': ['Ischial spine', 'AIIS', 'Pubic symphysis'],
    # Neck muscles
    'manubrium of the sternum': ['Body of the sternum', 'Xiphoid process', 'Medial clavicle'],
    'sternocleidomastoid': ['Splenius capitis', 'Anterior scalene', 'Levator scapulae'],
    'scalenes': ['Sternocleidomastoid', 'Levator scapulae', 'Splenius capitis'],
    'splenius capitis': ['Sternocleidomastoid', 'Semispinalis capitis', 'Splenius cervicis'],
    'mastoid process': ['Transverse processes of C1-C4', 'External occipital protuberance', 'Superior nuchal line'],
    # Trunk muscles
    'quadratus lumborum': ['Erector spinae', 'External obliques', 'Internal obliques'],
    'external obliques': ['Internal obliques', 'Transversus abdominis', 'Rectus abdominis'],
    'internal obliques': ['External obliques', 'Transversus abdominis', 'Rectus abdominis'],
    'laterally flex the trunk and rotate it to the same side': ['Laterally flex the trunk and rotate it to the opposite side', 'Flex the trunk and rotate it to the same side', 'Extend the trunk and rotate it to the same side'],
    'laterally flex the trunk and rotate it to the opposite side': ['Laterally flex the trunk and rotate it to the same side', 'Flex the trunk and rotate it to the opposite side', 'Extend the trunk and rotate it to the opposite side'],
    'origin of external obliques': ['Insertion of external obliques', 'Origin of internal obliques', 'Origin of transversus abdominis'],
    'rectus abdominis': ['External obliques', 'Transversus abdominis', 'Internal obliques'],
    # Breathing muscles
    'all answers are correct': ['Only the first answer is correct', 'Only the first two answers are correct', 'None of the answers are correct'],
    # Multi-answer overrides (keyed by first correct answer lowercase)
    'all of the above': ['Only the first answer is correct', 'Only the first two answers are correct', 'None of the answers are correct'],
    'diaphragm': ['External intercostals', 'Internal intercostals', 'Scalenes'],
    'internal intercostals': ['External intercostals', 'Diaphragm', 'Transversus abdominis'],
    'external intercostals': ['Internal intercostals', 'Diaphragm', 'Serratus anterior'],
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
    # Check targeted overrides first (research-backed best distractors)
    correct_lower = correct_answer.lower().strip()
    if correct_lower in TARGETED_DISTRACTORS:
        targeted = TARGETED_DISTRACTORS[correct_lower]
        if len(targeted) >= 3:
            return targeted[:3]

    pool = SECTION_POOLS.get(section_id, {})

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


# ── RE-PARSE QUESTIONS FROM XLSX WITH CORRECT IMAGE MAPPING ──
# Don't trust the raw JSON's image field - rebuild from XML-based IMAGE_ROW_MAP

import openpyxl
wb = openpyxl.load_workbook('data/quiz-study-guide.xlsx')
ws = wb['Sheet1']

sections_def = [
    (1, 358, 'general-anatomy', 'General Anatomy & Movement'),
    (359, 555, 'muscle-contractions', 'Muscle Contractions'),
    (556, 655, 'forearm', 'Muscles That Move the Forearm'),
    (656, 803, 'scapula', 'Muscles That Move the Scapula'),
    (804, 993, 'shoulder', 'Muscles That Move the Shoulder'),
    (994, 1081, 'knee', 'Muscles That Move the Knee'),
    (1082, 1181, 'ankle', 'Muscles That Move the Ankle'),
    (1182, 1440, 'hip', 'Muscles That Move the Hip'),
    (1441, 1567, 'neck', 'Muscles That Move the Neck'),
    (1568, 1704, 'trunk', 'Muscles That Move the Trunk'),
    (1705, 1771, 'breathing', 'Muscles Involved With Breathing'),
]

parsed_questions = []
parsed_sections = []
q_id = 0

for start, end, slug, name in sections_def:
    current_q = None
    questions_in_section = []

    for row_idx in range(start, end + 1):
        cell = ws.cell(row=row_idx, column=1)
        val = cell.value
        if val is None:
            continue
        val = str(val).strip()

        if cell.fill and cell.fill.start_color:
            rgb = str(cell.fill.start_color.rgb)
            if 'FFFF' in rgb.upper() and not re_mod.match(r'^Question\s+\d+', val):
                continue

        m = re_mod.match(r'^Question\s+(\d+)', val)
        if m:
            if current_q:
                questions_in_section.append(current_q)
            q_id += 1
            current_q = {
                'id': q_id,
                'section': slug,
                'questionNum': int(m.group(1)),
                'text': '',
                'answers': [],
                'image': None,
                'type': 'single',
                '_startRow': row_idx
            }
        elif current_q:
            if val == 'True or False':
                current_q['type'] = 'tf'
            elif '(Select all that apply)' in val:
                current_q['type'] = 'multi'
                current_q['text'] = val
            elif not current_q['text']:
                current_q['text'] = val
            else:
                current_q['answers'].append(val)

    if current_q:
        questions_in_section.append(current_q)

    # Auto-detect multi-answer questions: if >1 answers and not T/F, mark as multi
    for q in questions_in_section:
        if q['type'] == 'single' and len(q['answers']) > 1:
            q['type'] = 'multi'

    # Map images using the CORRECT XML-based IMAGE_ROW_MAP
    for idx, q in enumerate(questions_in_section):
        q_start = q['_startRow']
        q_end = questions_in_section[idx + 1]['_startRow'] if idx + 1 < len(questions_in_section) else end + 1

        for img_row, img_file in IMAGE_ROW_MAP.items():
            if q_start <= img_row < q_end:
                q['image'] = img_file
                break

        del q['_startRow']

    # ── SHARED IMAGE ASSIGNMENTS ──
    # Some questions reference "the image shows" / "bony landmark shown" but the XLSX
    # only embeds the image once at a nearby question's row. These manual overrides
    # assign the correct shared image based on anatomy cross-referencing.
    SHARED_IMAGES = {
        # Q text contains "bony landmark shown" → Coracoid process; image10 shows same landmark
        ('forearm', 'Coracoid process'): 'image10.jpeg',
        # Q text contains "bony landmark shown" → Biceps femoris inserts on head of fibula
        ('knee', 'Biceps femoris'): 'image34.jpeg',
        # Q text contains "image shows" → Scalenes; image44 is the scalenes image
        ('neck', 'Scalenes'): 'image44.jpeg',
    }
    for q in questions_in_section:
        if q.get('image'):
            continue
        q_text = q.get('question', '').lower()
        if 'image' not in q_text and 'shown' not in q_text:
            continue
        for ans in q['answers']:
            key = (slug, ans)
            if key in SHARED_IMAGES:
                q['image'] = SHARED_IMAGES[key]
                break

    parsed_sections.append({'id': slug, 'name': name, 'questionCount': len(questions_in_section)})
    parsed_questions.extend(questions_in_section)

print(f"Parsed {len(parsed_questions)} questions, {sum(1 for q in parsed_questions if q['image'])} with images")

# Rebuild section_answers from fresh parse
section_answers = {}
for q in parsed_questions:
    sec = q['section']
    if sec not in section_answers:
        section_answers[sec] = set()
    for ans in q['answers']:
        section_answers[sec].add(ans)

# ── FIX "ALL ANSWERS ARE CORRECT" QUESTIONS ──
# These questions in the XLSX have "All Answers are Correct" as the answer but don't
# list what the actual answer choices are. Convert to proper multi-select with real answers.
ALL_ANSWERS_OVERRIDES = {
    'Muscles function to:': {
        'correctAnswers': ['stabilize something', 'prevent something from moving', 'make something move'],
        'wrongAnswers': ['Produce red blood cells', 'Store calcium', 'Transmit nerve impulses'],
    },
    'Which of the following muscles inserts on the greater trochanter?': {
        'correctAnswers': ['Gluteus medius', 'Gluteus minimus', 'Piriformis'],
        'wrongAnswers': ['Gluteus maximus', 'Sartorius', 'Gracilis'],
    },
    'Which muscle acts to laterally flex the head to the same side?': {
        'correctAnswers': ['Sternocleidomastoid', 'Scalenes', 'Splenius capitis', 'Splenius cervicis'],
        'wrongAnswers': ['Trapezius', 'Semispinalis capitis', 'Longus colli'],
    },
    'The diaphragm:': {
        'correctAnswers': ['Is the primary muscle of inspiration', 'Separates the thoracic and abdominal cavities', 'Is dome-shaped at rest'],
        'wrongAnswers': ['Is an accessory breathing muscle', 'Contracts during exhalation only', 'Is located in the abdominal cavity'],
    },
}

for q in parsed_questions:
    if any(a.lower().startswith('all') and 'correct' in a.lower() for a in q['answers']):
        override = ALL_ANSWERS_OVERRIDES.get(q['question'])
        if override:
            q['answers'] = override['correctAnswers']
            q['_wrongAnswers'] = override['wrongAnswers']
            q['type'] = 'multi'
    # Also strip 'All of the above' from multi-answer correct lists
    if q['type'] == 'multi':
        q['answers'] = [a for a in q['answers'] if a.lower() not in ('all of the above', 'all answers are correct')]

# ── BUILD OUTPUT ──
output = {
    'version': 1,
    'sections': parsed_sections,
    'questions': [],
}

for q in parsed_questions:
    if not q['answers']:
        continue

    correct_answers = q['answers']  # Always a list
    section_correct = list(section_answers.get(q['section'], set()))

    if q['type'] == 'tf':
        # True/False: single correct, one wrong
        correct_answers = [correct_answers[0]]
        if correct_answers[0].lower() == 'true':
            distractors = ['False']
        else:
            distractors = ['True']
    elif q['type'] == 'multi':
        # Use pre-set wrong answers if available (from ALL_ANSWERS_OVERRIDES)
        if '_wrongAnswers' in q:
            distractors = q['_wrongAnswers']
        else:
            # Multi-answer: generate distractors that are NOT any of the correct answers
            # and are in the same category as the correct answers
            correct_lower_set = {a.lower().strip() for a in correct_answers}
            pool = SECTION_POOLS.get(q['section'], {})

            # Classify first correct answer to find the right category
            answer_category = classify_answer(correct_answers[0], pool)

            # Get same-category candidates from pool + section
            candidates = []
            seen = set(correct_lower_set)

            # Same category from pool first
            if answer_category and answer_category in pool:
                for v in pool[answer_category]:
                    vl = v.lower().strip()
                    if vl not in seen:
                        candidates.append(v)
                        seen.add(vl)

            # Same category from section answers
            for a in section_correct:
                al = a.lower().strip()
                if al not in seen:
                    a_cat = classify_answer(a, pool)
                    if a_cat == answer_category:
                        candidates.append(a)
                        seen.add(al)

            # Any remaining section answers
            for a in section_correct:
                al = a.lower().strip()
                if al not in seen:
                    candidates.append(a)
                    seen.add(al)

            random.shuffle(candidates)
            # Need enough wrong answers so total options >= 4 (or at least 2 wrong)
            needed = max(2, 4 - len(correct_answers))
            distractors = candidates[:needed]

            if len(distractors) < needed:
                # Pull more from all pool values
                all_pool = []
                for values in pool.values():
                    all_pool.extend(values)
                random.shuffle(all_pool)
                for c in all_pool:
                    if len(distractors) >= needed:
                        break
                    cl = c.lower().strip()
                    if cl not in seen:
                        distractors.append(c)
                        seen.add(cl)

            if len(distractors) < needed:
                padding = ['None of the above', 'Cannot be determined']
                for p in padding:
                    if len(distractors) >= needed:
                        break
                    if p.lower() not in seen:
                        distractors.append(p)
            distractors = distractors[:needed]
    else:
        # Single answer
        correct_answers = [correct_answers[0]]
        distractors = get_distractors(q['text'], correct_answers[0], q['section'], section_correct)
        min_distractors = 3
        if len(distractors) < min_distractors:
            padding = ['None of the above', 'All of the above', 'Cannot be determined']
            for p in padding:
                if len(distractors) >= min_distractors:
                    break
                if p.lower() != correct_answers[0].lower():
                    distractors.append(p)
        distractors = distractors[:3]

    question_obj = {
        'id': q['id'],
        'section': q['section'],
        'question': q['text'],
        'type': q['type'],  # 'single', 'multi', 'tf'
        'correctAnswers': correct_answers,
        'wrongAnswers': distractors,
        'explanation': build_explanation(q['text'], ', '.join(correct_answers), q['type']),
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
print(f"  Single: {sum(1 for q in output['questions'] if q['type'] == 'single')}")
print(f"  Multi-answer: {sum(1 for q in output['questions'] if q['type'] == 'multi')}")
print(f"  T/F: {sum(1 for q in output['questions'] if q['type'] == 'tf')}")
print(f"  With images: {sum(1 for q in output['questions'] if q['image'])}")

# Verify no correct answer appears in wrong answers
overlaps = 0
for q in output['questions']:
    correct_set = {a.lower().strip() for a in q['correctAnswers']}
    for w in q['wrongAnswers']:
        if w.lower().strip() in correct_set:
            overlaps += 1
            print(f"  OVERLAP: Q{q['id']} correct '{q['correctAnswers']}' has wrong '{w}'")
if overlaps == 0:
    print("No overlaps between correct and wrong answers!")

# Verify distractor counts
bad = 0
for q in output['questions']:
    min_needed = 1 if q['type'] == 'tf' else 2
    if len(q['wrongAnswers']) < min_needed:
        bad += 1
        print(f"  WARNING: Q{q['id']} has only {len(q['wrongAnswers'])} distractors")
if bad == 0:
    print("All questions have sufficient distractors!")
