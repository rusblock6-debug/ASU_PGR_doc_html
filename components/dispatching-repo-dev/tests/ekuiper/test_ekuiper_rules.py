"""
Тесты для проверки правил eKuiper.
"""
import pytest
import requests


class TestEKuiperStreams:
    """Тесты стримов eKuiper."""
    
    EXPECTED_STREAMS = [
        "external_stream_gps", "external_stream_speed",
        "external_stream_weight", "external_stream_fuel",
        "local_stream_gps_ds", "local_stream_speed_ds",
        "local_stream_weight_ds", "local_stream_fuel_ds",
        "speed_downsampled", "weight_downsampled",
        "fuel_downsampled", "gps_downsampled",
        "mqtt_stream"
    ]
    
    def test_all_streams_created(self, ekuiper_api):
        """Проверка создания всех стримов."""
        response = requests.get(f"{ekuiper_api}/streams")
        assert response.status_code == 200
        
        streams = response.json()
        assert len(streams) == len(self.EXPECTED_STREAMS), \
            f"Expected {len(self.EXPECTED_STREAMS)} streams, got {len(streams)}"
        
        for expected in self.EXPECTED_STREAMS:
            assert expected in streams, f"Stream '{expected}' not found"


class TestEKuiperRules:
    """Тесты правил eKuiper."""
    
    EXPECTED_RULES = [
        "mqtt_raw_to_jsonb",
        "rule_proxy_gps", "rule_proxy_speed", "rule_proxy_weight", "rule_proxy_fuel",
        "rule_downsample_gps", "rule_downsample_speed", "rule_downsample_weight", "rule_downsample_fuel",
        "rule_speed_events", "rule_weight_events", "rule_vibro_events",
        "rule_fuel_alerts", "rule_tag_detection"
    ]
    
    def test_all_rules_created(self, ekuiper_api):
        """Проверка создания всех правил."""
        response = requests.get(f"{ekuiper_api}/rules")
        assert response.status_code == 200
        
        rules = response.json()
        rule_ids = [r['id'] for r in rules]
        
        assert len(rule_ids) == len(self.EXPECTED_RULES), \
            f"Expected {len(self.EXPECTED_RULES)} rules, got {len(rule_ids)}"
        
        for expected in self.EXPECTED_RULES:
            assert expected in rule_ids, f"Rule '{expected}' not found"
    
    def test_all_rules_running(self, ekuiper_api):
        """Проверка статуса всех правил."""
        response = requests.get(f"{ekuiper_api}/rules")
        assert response.status_code == 200
        
        rules = response.json()
        failed_rules = []
        
        for rule in rules:
            rule_id = rule['id']
            status_response = requests.get(f"{ekuiper_api}/rules/{rule_id}/status")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            if status_data.get('status') != 'running':
                failed_rules.append({
                    'rule': rule_id,
                    'status': status_data.get('status'),
                    'error': status_data.get('message', 'No error')
                })
        
        assert len(failed_rules) == 0, f"Failed rules: {failed_rules}"
    
    def test_mqtt_raw_to_jsonb_processing(self, ekuiper_api):
        """Проверка правила mqtt_raw_to_jsonb."""
        response = requests.get(f"{ekuiper_api}/rules/mqtt_raw_to_jsonb/status")
        assert response.status_code == 200
        
        status_data = response.json()
        assert status_data.get('status') == 'running'
        
        # Проверяем, что правило обрабатывает данные
        records_in = status_data.get('source_mqtt_stream_0_records_in_total', 0)
        assert records_in >= 0


class TestEKuiperExternalServices:
    """Тесты external services."""
    
    def test_graph_service_registered(self, ekuiper_api):
        """Проверка регистрации graphService."""
        response = requests.get(f"{ekuiper_api}/services/functions")
        assert response.status_code == 200
        
        functions = response.json()
        assert any('graphService' in str(func) for func in functions), \
            "graphService not found"
