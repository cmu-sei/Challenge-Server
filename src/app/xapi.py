#!/usr/bin/env python3
#
# Challenge Server
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#

"""
xAPI Profile Implementation

Provides a profile-driven xAPI Learning Record Provider with three operating levels:
- Level 0: Telemetry Fragment Emitter (no actor/context)
- Level 1: Standalone xAPI LRP (actor, no cmi5)
- Level 2: cmi5-Allowed Statement LRP (actor + cmi5 context)

Architecture follows Challenge Server pattern: single file per feature.
"""

import json
import os
import uuid
import datetime
import copy
import time
import logging
from typing import Dict, List, Optional, Any, Union
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# ============================================================================
# PROFILE ENGINE
# ============================================================================

class ProfileEngine:
    """
    xAPI Profile Engine - Loads and resolves xAPI profile concepts.
    """

    def __init__(self, profile_paths: List[str], basedir: str = None):
        """Initialize the Profile Engine."""
        self.basedir = basedir or os.path.dirname(os.path.abspath(__file__))

        # Profile indexes
        self.verbs: Dict[str, dict] = {}
        self.activity_types: Dict[str, dict] = {}
        self.extensions: Dict[str, dict] = {}
        self.templates: List[dict] = []
        self.patterns: Dict[str, dict] = {}
        self.profile_version_iris: List[str] = []

        # Shorthand lookups
        self._verb_by_preflabel: Dict[str, str] = {}
        self._extension_by_preflabel: Dict[str, str] = {}

        # Load profiles
        if not profile_paths:
            logger.info("[xapi] No profiles specified, using built-in ADL profile")
            profile_paths = [os.path.join(self.basedir, "profiles", "adl.jsonld")]

        for path in profile_paths:
            try:
                profile = self._load_profile(path)
                self._index_profile(profile)
            except Exception as e:
                logger.error(f"[xapi] Failed to load profile {path}: {e}")
                raise

    def _load_profile(self, path_or_url: str) -> dict:
        """Load profile from URL or local path with automatic fallback."""
        if path_or_url.startswith(('http://', 'https://')):
            try:
                logger.info(f"[xapi] Fetching remote profile from {path_or_url}")
                profile = self._fetch_remote_profile(path_or_url)
                logger.info(f"[xapi] Successfully fetched remote profile")
                self._validate_profile(profile)
                return profile
            except Exception as e:
                logger.warning(f"[xapi] Failed to fetch remote profile {path_or_url}: {e}")
                logger.info(f"[xapi] Falling back to bundled local profile")
                local_path = self._map_url_to_local(path_or_url)
                if not local_path:
                    raise ValueError(f"No local fallback available for {path_or_url}")
                return self._load_local_profile(local_path)
        else:
            logger.info(f"[xapi] Loading local profile from {path_or_url}")
            return self._load_local_profile(path_or_url)

    def _fetch_remote_profile(self, url: str) -> dict:
        """Fetch profile from remote URL."""
        import requests
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    def _load_local_profile(self, path: str) -> dict:
        """Load profile from local filesystem."""
        if not os.path.isabs(path):
            path = os.path.join(self.basedir, path)

        with open(path, 'r', encoding='utf-8') as f:
            profile = json.load(f)

        self._validate_profile(profile)
        return profile

    def _map_url_to_local(self, url: str) -> Optional[str]:
        """Map known profile URLs to bundled local copies."""
        url = url.rstrip('/')
        mappings = {
            'https://w3id.org/xapi/adl': 'profiles/adl.jsonld',
            'https://w3id.org/xapi/cmi5': 'profiles/cmi5.jsonld',
            'http://adlnet.gov/expapi': 'profiles/adl.jsonld',
        }
        return mappings.get(url, None)

    def _validate_profile(self, profile: dict) -> None:
        """Validate profile structure."""
        if not isinstance(profile, dict):
            raise ValueError("Profile must be a dictionary")
        if '@context' not in profile:
            logger.warning("[xapi] Profile missing @context (not valid JSON-LD)")
        if 'id' not in profile:
            raise ValueError("Profile must have an 'id' field")
        if profile.get('type') != 'Profile':
            logger.warning(f"[xapi] Profile type is '{profile.get('type')}', expected 'Profile'")

    def _index_profile(self, profile: dict) -> None:
        """Index profile concepts for fast lookup."""
        profile_id = profile.get('id', 'unknown')
        logger.info(f"[xapi] Indexing profile: {profile_id}")

        if profile_id:
            self.profile_version_iris.append(profile_id)

        # Handle both formats:
        # 1. Standard: verbs/extensions/activityTypes/templates/patterns as separate arrays
        # 2. Unified: concepts array with type field

        # Check for unified concepts array (Navy profile format)
        concepts = profile.get('concepts', [])
        if concepts:
            for concept in concepts:
                concept_type = concept.get('type')
                concept_id = concept.get('id')

                if concept_type == 'Verb' and concept_id:
                    self.verbs[concept_id] = concept
                    preflabel = self._get_label(concept.get('prefLabel', {}))
                    if preflabel:
                        self._verb_by_preflabel[preflabel.lower()] = concept_id

                elif concept_type == 'ActivityType' and concept_id:
                    self.activity_types[concept_id] = concept

                elif concept_type in ['ActivityExtension', 'ContextExtension', 'ResultExtension'] and concept_id:
                    self.extensions[concept_id] = concept
                    preflabel = self._get_label(concept.get('prefLabel', {}))
                    if preflabel:
                        self._extension_by_preflabel[preflabel.lower()] = concept_id

                elif concept_type == 'StatementTemplate':
                    self.templates.append(concept)

                elif concept_type == 'Pattern' and concept_id:
                    self.patterns[concept_id] = concept

        # Standard format (separate arrays)
        # Index verbs
        for verb in profile.get('verbs', []):
            verb_id = verb.get('id')
            if verb_id:
                self.verbs[verb_id] = verb
                preflabel = self._get_label(verb.get('prefLabel', {}))
                if preflabel:
                    self._verb_by_preflabel[preflabel.lower()] = verb_id

        # Index activity types
        for activity_type in profile.get('activityTypes', []):
            at_id = activity_type.get('id')
            if at_id:
                self.activity_types[at_id] = activity_type

        # Index extensions
        for extension in profile.get('extensions', []):
            ext_id = extension.get('id')
            if ext_id:
                self.extensions[ext_id] = extension
                preflabel = self._get_label(extension.get('prefLabel', {}))
                if preflabel:
                    self._extension_by_preflabel[preflabel.lower()] = ext_id

        # Index templates
        for template in profile.get('templates', []):
            self.templates.append(template)

        # Index patterns
        for pattern in profile.get('patterns', []):
            pattern_id = pattern.get('id')
            if pattern_id:
                self.patterns[pattern_id] = pattern

        logger.info(f"[xapi] Profile indexed: {len(self.verbs)} verbs, {len(self.extensions)} extensions, {len(self.templates)} templates")

    def _get_label(self, lang_map: dict) -> str:
        """Get label from language map with fallback (en-US → en → first)."""
        if not isinstance(lang_map, dict):
            return ""
        if 'en-US' in lang_map:
            return lang_map['en-US']
        if 'en' in lang_map:
            return lang_map['en']
        if lang_map:
            return next(iter(lang_map.values()))
        return ""

    def resolve_verb(self, shorthand: str) -> Optional[str]:
        """Resolve verb shorthand to full IRI."""
        if shorthand.startswith(('http://', 'https://')):
            return shorthand
        verb_iri = self._verb_by_preflabel.get(shorthand.lower())
        if verb_iri:
            return verb_iri
        logger.warning(f"[xapi] Unknown verb shorthand: {shorthand}")
        return None

    def get_verb_display(self, verb_iri: str) -> str:
        """Get verb display name from IRI."""
        verb = self.verbs.get(verb_iri, {})
        display = self._get_label(verb.get('prefLabel', {}))
        if display:
            return display
        return verb_iri.split('/')[-1]

    def find_template(self, verb_iri: str, object_activity_type: str = None) -> Optional[dict]:
        """Find statement template matching verb and object type."""
        for template in self.templates:
            verb_rule = template.get('verb')
            if verb_rule and verb_iri != verb_rule:
                continue
            if object_activity_type:
                obj_type_rule = template.get('objectActivityType')
                if obj_type_rule and object_activity_type != obj_type_rule:
                    continue
            return template
        return None

    def auto_map_data(self, data: dict, template: dict) -> Dict[str, Any]:
        """Auto-map data keys to extension locations via prefLabel."""
        if not data or not template:
            return {}

        mapped = {}
        rules = template.get('rules', [])

        for key, value in data.items():
            ext_id = self._extension_by_preflabel.get(key.lower())
            if not ext_id:
                logger.warning(f"[xapi] Unknown extension prefLabel: {key}")
                continue

            for rule in rules:
                if rule.get('location') and ext_id in rule.get('location', ''):
                    location = rule.get('location')
                    mapped[location] = value
                    break

        return mapped


# ============================================================================
# STATEMENT BUILDER
# ============================================================================

class StatementBuilder:
    """xAPI Statement Builder - Builds statements at three levels."""

    def __init__(self, engine: ProfileEngine):
        self.engine = engine

    def build(self,
              level: int,
              verb_shorthand: str,
              activity_id: str,
              question_label: str,
              question_text: str,
              question_mode: str = None,
              question_opts: dict = None,
              user_answer: str = '',
              success: bool = True,
              xapi_data: dict = None,
              actor: dict = None,
              registration: str = None,
              context_template: dict = None) -> dict:
        """Build xAPI statement or fragment."""

        statement_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc)

        # Resolve verb
        verb_iri = self.engine.resolve_verb(verb_shorthand)
        if not verb_iri:
            logger.error(f"[xapi] Cannot resolve verb: {verb_shorthand}")
            verb_iri = "http://adlnet.gov/expapi/verbs/answered"

        verb_display = self.engine.get_verb_display(verb_iri)

        # Find template
        template = self.engine.find_template(verb_iri)

        # Build object definition
        definition = {
            "name": {"en-US": question_label},
            "description": {"en-US": question_text}
        }

        # Get objectActivityType from template
        if template and 'objectActivityType' in template:
            definition["type"] = template['objectActivityType']

        # CRITICAL: Only add interactionType if BOTH conditions met
        if verb_iri == "http://adlnet.gov/expapi/verbs/answered" and question_mode:
            self._add_interaction_type(definition, question_mode, question_opts)

        # Build base statement
        statement = {
            "id": statement_id,
            "verb": {
                "id": verb_iri,
                "display": {"en-US": verb_display}
            },
            "object": {
                "objectType": "Activity",
                "id": activity_id if activity_id else f"challenge#{question_label}",
                "definition": definition
            },
            "result": {
                "success": success,
                "response": user_answer
            },
            "context": {
                "contextActivities": {
                    "category": []
                }
            },
            "timestamp": now.isoformat()
        }

        # Auto-map extension data
        if xapi_data and template:
            mapped = self.engine.auto_map_data(xapi_data, template)
            for location, value in mapped.items():
                self._set_nested_value(statement, location, value)

        # Add profile version IRIs as category
        for profile_iri in self.engine.profile_version_iris:
            statement["context"]["contextActivities"]["category"].append({
                "id": profile_iri,
                "objectType": "Activity"
            })

        # Level-specific processing
        if level == 0:
            # Level 0: Telemetry fragments (no actor, no context)
            statement.pop('actor', None)
            statement.pop('context', None)
            return statement
        elif level == 1:
            if actor:
                statement["actor"] = actor
            return statement
        elif level == 2:
            if actor:
                statement["actor"] = actor
            if registration or context_template:
                statement = self._apply_cmi5_context(statement, registration, context_template)
            return statement
        else:
            logger.error(f"[xapi] Invalid level: {level}")
            return statement

    def _add_interaction_type(self, definition: dict, mode: str, opts: dict) -> None:
        """Map application question types to xAPI interaction types."""
        if mode == 'mc' and isinstance(opts, dict):
            definition["interactionType"] = "choice"
            definition["choices"] = [
                {"id": key, "description": {"en-US": value}}
                for key, value in opts.items()
            ]
        elif mode == 'text' or mode == 'text_single':
            definition["interactionType"] = "fill-in"
        elif mode == 'button':
            definition["interactionType"] = "performance"
        elif mode == 'tf':
            definition["interactionType"] = "true-false"
        else:
            definition["interactionType"] = "other"

    def _apply_cmi5_context(self, statement: dict, registration: str,
                            context_template: dict) -> dict:
        """Apply cmi5-allowed statement requirements."""
        if registration:
            statement["context"]["registration"] = registration

        if context_template:
            template_copy = copy.deepcopy(context_template)

            # Merge extensions
            template_exts = template_copy.get('extensions', {})
            if template_exts:
                if 'extensions' not in statement["context"]:
                    statement["context"]["extensions"] = {}
                statement["context"]["extensions"].update(template_exts)

            # Merge contextActivities
            template_activities = template_copy.get('contextActivities', {})
            if template_activities:
                if 'contextActivities' not in statement["context"]:
                    statement["context"]["contextActivities"] = {}

                for activity_type in ['parent', 'grouping', 'category', 'other']:
                    template_list = template_activities.get(activity_type, [])
                    if template_list:
                        if activity_type not in statement["context"]["contextActivities"]:
                            statement["context"]["contextActivities"][activity_type] = []
                        existing_ids = {
                            act.get('id') for act in statement["context"]["contextActivities"][activity_type]
                        }
                        for act in template_list:
                            if act.get('id') not in existing_ids:
                                statement["context"]["contextActivities"][activity_type].append(act)

        # Strip cmi5 category (this is cmi5-allowed, not cmi5-defined)
        cmi5_category_id = "https://w3id.org/xapi/cmi5/context/categories/cmi5"
        categories = statement["context"]["contextActivities"].get("category", [])
        statement["context"]["contextActivities"]["category"] = [
            cat for cat in categories if cat.get('id') != cmi5_category_id
        ]

        # Add moveOn category if result.success or result.completion present
        result = statement.get('result', {})
        if 'success' in result or 'completion' in result:
            moveon_category = {
                "id": "https://w3id.org/xapi/cmi5/context/categories/moveon",
                "objectType": "Activity"
            }
            moveon_present = any(
                cat.get('id') == moveon_category['id']
                for cat in statement["context"]["contextActivities"]["category"]
            )
            if not moveon_present:
                statement["context"]["contextActivities"]["category"].append(moveon_category)

        return statement

    def _set_nested_value(self, obj: dict, path: str, value: Any) -> None:
        """Set nested value using JSONPath-like string."""
        if path.startswith('$.'):
            path = path[2:]

        segments = self._parse_jsonpath(path)

        current = obj
        for segment in segments[:-1]:
            if segment not in current:
                current[segment] = {}
            current = current[segment]

        current[segments[-1]] = value

    def _parse_jsonpath(self, path: str) -> list:
        """Parse JSONPath into segments."""
        segments = []
        current = ""
        in_bracket = False

        for char in path:
            if char == '[':
                if current:
                    segments.append(current)
                    current = ""
                in_bracket = True
            elif char == ']':
                in_bracket = False
            elif char == '.' and not in_bracket:
                if current:
                    segments.append(current)
                    current = ""
            elif char in ('"', "'"):
                continue
            else:
                current += char

        if current:
            segments.append(current)

        return segments


# ============================================================================
# VALIDATOR
# ============================================================================

class StatementValidator:
    """xAPI Statement Validator - Validates statements against templates."""

    def __init__(self, engine: ProfileEngine):
        self.engine = engine

    def validate(self, statement: dict, template: dict) -> List[str]:
        """Validate statement against template rules."""
        warnings = []

        if not template:
            return warnings

        rules = template.get('rules', [])

        for rule in rules:
            location = rule.get('location')
            presence = rule.get('presence')

            if not location:
                continue

            value = self._get_nested_value(statement, location)

            # Check presence
            if presence == 'included':
                if value is None:
                    warnings.append(f"Required field missing: {location}")
            elif presence == 'excluded':
                if value is not None:
                    warnings.append(f"Forbidden field present: {location}")
            elif presence == 'recommended':
                if value is None:
                    warnings.append(f"Recommended field missing: {location}")

        return warnings

    def _get_nested_value(self, obj: dict, path: str) -> Any:
        """Get nested value using JSONPath-like string."""
        if path.startswith('$.'):
            path = path[2:]

        segments = self._parse_jsonpath(path)

        current = obj
        for segment in segments:
            if isinstance(current, dict):
                current = current.get(segment)
                if current is None:
                    return None
            else:
                return None

        return current

    def _parse_jsonpath(self, path: str) -> list:
        """Parse JSONPath into segments."""
        segments = []
        current = ""
        in_bracket = False

        for char in path:
            if char == '[':
                if current:
                    segments.append(current)
                    current = ""
                in_bracket = True
            elif char == ']':
                in_bracket = False
            elif char == '.' and not in_bracket:
                if current:
                    segments.append(current)
                    current = ""
            elif char in ('"', "'"):
                continue
            else:
                current += char

        if current:
            segments.append(current)

        return segments


# ============================================================================
# TRANSPORT
# ============================================================================

class FileTransport:
    """File Transport - Writes statements to file for external consumer."""

    def __init__(self, file_path: str, format: str = "jsonl"):
        self.file_path = file_path
        self.format = format
        dir_path = os.path.dirname(file_path)
        if dir_path:  # Only create directory if path contains one
            os.makedirs(dir_path, exist_ok=True)

    def send(self, statement: dict) -> bool:
        """Append statement to file."""
        try:
            with open(self.file_path, 'a', encoding='utf-8') as f:
                json.dump(statement, f, ensure_ascii=False)
                f.write('\n')
            logger.info(f"[xapi] Statement written to file: {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"[xapi] Failed to write statement to file: {e}")
            return False


class HTTPTransport:
    """HTTP Transport - Sends statements directly to LRS via HTTP."""

    def __init__(self, endpoint: str, auth_token: str,
                 xapi_version: str = "2.0.0",
                 max_retries: int = 3):
        self.endpoint = endpoint.rstrip('/')
        self.auth_token = auth_token
        self.xapi_version = xapi_version
        self.max_retries = max_retries

    def send(self, statement: dict) -> bool:
        """Send statement to LRS via HTTP PUT."""
        import requests

        statement_id = statement.get('id')
        url = f"{self.endpoint}/statements?statementId={statement_id}"

        headers = {
            "Content-Type": "application/json",
            "X-Experience-API-Version": self.xapi_version,
            "Authorization": self.auth_token
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.put(url, json=statement, headers=headers, timeout=10, verify=False)

                if response.status_code in (200, 204):
                    verb_id = statement.get('verb', {}).get('id', '')
                    logger.info(f"[xapi] Statement sent to LRS (verb={verb_id}, id={statement_id})")
                    return True
                else:
                    logger.warning(f"[xapi] LRS returned {response.status_code}: {response.text}")
                    if response.status_code >= 500 and attempt < self.max_retries - 1:
                        wait = 2 ** attempt
                        logger.info(f"[xapi] Retrying in {wait}s...")
                        time.sleep(wait)
                        continue
                    else:
                        return False

            except requests.exceptions.RequestException as e:
                logger.error(f"[xapi] HTTP request failed: {e}")
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    logger.info(f"[xapi] Retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                else:
                    return False

        return False


# ============================================================================
# ENGINE (Public API)
# ============================================================================

# Module-level singletons
_engine: Optional[ProfileEngine] = None
_builder: Optional[StatementBuilder] = None
_validator: Optional[StatementValidator] = None
_transport: Optional[Union[FileTransport, HTTPTransport]] = None


def initialize_xapi_engine() -> bool:
    """Initialize the xAPI engine at startup."""
    global _engine, _builder, _validator, _transport

    from app.extensions import globals

    try:
        logger.info("[xapi] Initializing xAPI engine")

        # Create ProfileEngine
        profile_paths = globals.xapi_profile_paths or []
        _engine = ProfileEngine(profile_paths, basedir=globals.basedir)
        logger.info(f"[xapi] ProfileEngine initialized with {len(profile_paths)} profiles")

        # Create StatementBuilder
        _builder = StatementBuilder(_engine)
        logger.info("[xapi] StatementBuilder initialized")

        # Create StatementValidator
        _validator = StatementValidator(_engine)
        logger.info("[xapi] StatementValidator initialized")

        # Create Transport
        if globals.xapi_transport_mode == "http":
            if not globals.xapi_transport_endpoint:
                logger.error("[xapi] HTTP transport requires endpoint")
                return False
            if not globals.xapi_transport_auth:
                logger.error("[xapi] HTTP transport requires auth_token")
                return False

            _transport = HTTPTransport(
                endpoint=globals.xapi_transport_endpoint,
                auth_token=globals.xapi_transport_auth,
                xapi_version=globals.xapi_version
            )
            logger.info(f"[xapi] HTTPTransport initialized (endpoint={globals.xapi_transport_endpoint})")

        else:
            _transport = FileTransport(
                file_path=globals.xapi_transport_file_path,
                format=globals.xapi_transport_format
            )
            logger.info(f"[xapi] FileTransport initialized (path={globals.xapi_transport_file_path})")

        globals.xapi_profile_loaded = True

        level = get_current_level()
        logger.info(f"[xapi] Engine initialized successfully at Level {level}")
        return True

    except Exception as e:
        logger.error(f"[xapi] Failed to initialize engine: {e}")
        return False


def send_xapi_statement(question_label: str,
                        question_config: dict,
                        user_answer: str,
                        success: bool) -> bool:
    """Build and send xAPI statement. Main API called by databaseHelpers.py."""
    global _engine, _builder, _validator, _transport

    from app.extensions import globals

    if not all([_engine, _builder, _validator, _transport]):
        logger.error("[xapi] Engine not initialized")
        return False

    try:
        level = get_current_level()

        question_text = question_config.get('text', '')
        question_mode = question_config.get('mode', '')
        question_opts = question_config.get('opts', {})

        xapi_config = question_config.get('xapi', {})
        verb_shorthand = xapi_config.get('verb', 'answered')
        xapi_data = xapi_config.get('data', {})

        activity_id = globals.xapi_activity_id or f"challenge#{question_label}"

        statement = _builder.build(
            level=level,
            verb_shorthand=verb_shorthand,
            activity_id=activity_id,
            question_label=question_label,
            question_text=question_text,
            question_mode=question_mode,
            question_opts=question_opts,
            user_answer=user_answer,
            success=success,
            xapi_data=xapi_data,
            actor=globals.xapi_actor if level >= 1 else None,
            registration=globals.xapi_registration if level == 2 else None,
            context_template=globals.xapi_context_template if level == 2 else None
        )

        template = _engine.find_template(
            _engine.resolve_verb(verb_shorthand) or "http://adlnet.gov/expapi/verbs/answered"
        )
        if template:
            warnings = _validator.validate(statement, template)
            if warnings:
                logger.warning(f"[xapi] Statement validation warnings: {warnings}")

        return _transport.send(statement)

    except Exception as e:
        logger.error(f"[xapi] Failed to send statement: {e}")
        return False


def get_current_level() -> int:
    """Get current operating level (0/1/2)."""
    from app.extensions import globals

    has_actor = bool(globals.xapi_actor)
    has_registration = bool(globals.xapi_registration)
    has_context_template = bool(globals.xapi_context_template)

    if not has_actor:
        return 0
    if has_actor and (has_registration or has_context_template):
        return 2
    return 1


def cmi5_send_answered(question_label: str, question_text: str,
                       user_answer: str, question_mode: str,
                       question_opts: dict, success: bool) -> bool:
    """
    Legacy function for existing databaseHelpers.py calls.
    DEPRECATED: Use send_xapi_statement() instead.
    """
    logger.warning("[xapi] cmi5_send_answered() is deprecated, use send_xapi_statement()")

    question_config = {
        'text': question_text,
        'mode': question_mode,
        'opts': question_opts,
        'xapi': {
            'verb': 'answered'
        }
    }

    return send_xapi_statement(question_label, question_config, user_answer, success)


# ============================================================================
# FLASK BLUEPRINT (REST API)
# ============================================================================

xapi_api = Blueprint('xapi_api', __name__)


@xapi_api.route('/context', methods=['POST'])
def set_context():
    """Set runtime xAPI context (actor, registration, contextTemplate)."""
    from app.extensions import globals

    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    # Update actor
    if 'actor' in data:
        actor = data['actor']
        has_ifi = any(key in actor for key in ['mbox', 'mbox_sha1sum', 'openid', 'account'])
        if not has_ifi:
            return jsonify({"error": "Actor must have at least one IFI"}), 400
        globals.xapi_actor = actor
        logger.info(f"[xapi] Actor updated via API")

    # Update registration
    if 'registration' in data:
        globals.xapi_registration = data['registration']
        logger.info(f"[xapi] Registration updated via API")

    # Update context template
    if 'context_template' in data:
        globals.xapi_context_template = data['context_template']
        logger.info(f"[xapi] Context template updated via API")

    # Update activity ID
    if 'activity_id' in data:
        globals.xapi_activity_id = data['activity_id']
        logger.info(f"[xapi] Activity ID updated via API")

    globals.xapi_context_received = bool(globals.xapi_actor)

    level = get_current_level()
    mode = ["fragment", "xapi", "cmi5-allowed"][level]

    return jsonify({
        "success": True,
        "level": level,
        "mode": mode,
        "actor_present": bool(globals.xapi_actor),
        "cmi5_context_present": bool(globals.xapi_registration or globals.xapi_context_template)
    })


@xapi_api.route('/context', methods=['GET'])
def get_context():
    """Get current operating level and context status."""
    from app.extensions import globals

    level = get_current_level()
    mode = ["fragment", "xapi", "cmi5-allowed"][level]

    return jsonify({
        "level": level,
        "mode": mode,
        "actor_present": bool(globals.xapi_actor),
        "cmi5_context_present": bool(globals.xapi_registration or globals.xapi_context_template),
        "profile_loaded": globals.xapi_profile_loaded,
        "xapi_enabled": globals.xapi_enabled
    })
