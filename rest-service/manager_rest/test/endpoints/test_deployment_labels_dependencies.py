
from mock import patch

from cloudify_rest_client.exceptions import CloudifyClientError

from manager_rest.rest.rest_utils import RecursiveDeploymentLabelsDependencies
from manager_rest.test import base_test
from manager_rest.test.attribute import attr
from manager_rest.test.base_test import BaseServerTestCase


@attr(client_min_version=3.1, client_max_version=base_test.LATEST_API_VERSION)
class DeploymentLabelsDependenciesTest(BaseServerTestCase):

    def _create_deployment_objects(self, parent_name, deployment_type, size):
        for service in range(1, size + 1):
            self.put_deployment_with_labels(
                [
                    {
                        'csys-obj-parent': parent_name
                    },
                    {
                        'csys-obj-type': deployment_type,
                    }
                ],
                resource_id='{0}_{1}_{2}'.format(
                    deployment_type, service, parent_name)
            )

    def _populate_deployment_labels_dependencies(self):
        self.put_mock_deployments('dep_0', 'dep_1')
        self.put_mock_deployments('dep_2', 'dep_3')
        self.put_mock_deployments('dep_4', 'dep_5')

        self.client.deployments.update_labels('dep_0', [
                {
                    'csys-obj-parent': 'dep_1'
                }
            ]
        )

        self.client.deployments.update_labels('dep_2', [
                {
                    'csys-obj-parent': 'dep_3'
                }
            ]
        )

        self.client.deployments.update_labels('dep_4', [
                {
                    'csys-obj-parent': 'dep_5'
                }
            ]
        )

    @patch('manager_rest.resource_manager.ResourceManager'
           '.handle_deployment_labels_graph')
    @patch('manager_rest.resource_manager.ResourceManager'
           '.verify_deployment_parent_labels')
    def test_deployment_with_empty_labels(self,
                                          verify_parents_mock,
                                          handle_labels_graph_mock):
        self.put_deployment('deployment_with_no_labels')
        verify_parents_mock.assert_not_called()
        handle_labels_graph_mock.assert_not_called()

    @patch('manager_rest.resource_manager.ResourceManager'
           '.handle_deployment_labels_graph')
    @patch('manager_rest.resource_manager.ResourceManager'
           '.verify_deployment_parent_labels')
    def test_deployment_with_non_parent_labels(self,
                                               verify_parents_mock,
                                               handle_labels_graph_mock):
        self.put_deployment_with_labels([{'env': 'aws'}, {'arch': 'k8s'}])
        verify_parents_mock.assert_not_called()
        handle_labels_graph_mock.assert_not_called()

    def test_deployment_with_single_parent_label(self):
        self.put_deployment('parent')
        self.put_deployment_with_labels([{'csys-obj-parent': 'parent'}])

        # deployment response
        deployment = self.client.deployments.get('parent')
        self.assertEqual(deployment.sub_services_count, 1)
        self.assertEqual(deployment.sub_environments_count, 0)

    def test_deployment_with_multiple_parent_labels(self):
        self.put_deployment(deployment_id='parent_1',
                            blueprint_id='blueprint_1')
        self.put_deployment(deployment_id='parent_2',
                            blueprint_id='blueprint_2')
        self.put_deployment_with_labels(
            [
                {
                    'csys-obj-parent': 'parent_1'
                },
                {
                    'csys-obj-parent': 'parent_2'
                }
            ]
        )
        deployment_1 = self.client.deployments.get('parent_1')
        deployment_2 = self.client.deployments.get('parent_2')
        self.assertEqual(deployment_1.sub_services_count, 1)
        self.assertEqual(deployment_1.sub_environments_count, 0)
        self.assertEqual(deployment_2.sub_services_count, 1)
        self.assertEqual(deployment_2.sub_environments_count, 0)

    def test_deployment_with_invalid_parent_label(self):
        error_message = 'label `csys-obj-parent` that does not exist'
        with self.assertRaisesRegex(CloudifyClientError, error_message):
            self.put_deployment_with_labels(
                [
                    {
                        'csys-obj-parent': 'notexist'
                    }
                ],
                resource_id='invalid_label_dep'
            )

    def test_deployment_with_valid_and_invalid_parent_labels(self):
        self.put_deployment(deployment_id='parent_1')
        error_message = 'label `csys-obj-parent` that does not exist'
        with self.assertRaisesRegex(CloudifyClientError, error_message):
            self.put_deployment_with_labels(
                [
                    {
                        'csys-obj-parent': 'parent_1'
                    },
                    {
                        'csys-obj-parent': 'notexist'
                    }
                ],
                resource_id='invalid_label_dep'
            )

    def test_add_valid_label_parent_to_created_deployment(self):
        self.put_deployment(deployment_id='parent_1',
                            blueprint_id='blueprint_1')
        self.put_deployment(deployment_id='parent_2',
                            blueprint_id='blueprint_2')
        self.put_deployment_with_labels([{'csys-obj-parent': 'parent_1'}],
                                        resource_id='label_dep')

        self.client.deployments.update_labels('label_dep', [
                {
                    'csys-obj-parent': 'parent_1'
                },
                {
                    'csys-obj-parent': 'parent_2'
                }
            ]
        )
        deployment_1 = self.client.deployments.get('parent_1')
        deployment_2 = self.client.deployments.get('parent_2')
        self.assertEqual(deployment_1.sub_services_count, 1)
        self.assertEqual(deployment_1.sub_environments_count, 0)
        self.assertEqual(deployment_2.sub_services_count, 1)
        self.assertEqual(deployment_2.sub_environments_count, 0)

    def test_add_invalid_label_parent_to_created_deployment(self):
        error_message = 'label `csys-obj-parent` that does not exist'
        self.put_deployment(deployment_id='parent_1',
                            blueprint_id='blueprint_1')
        self.put_deployment_with_labels([{'csys-obj-parent': 'parent_1'}],
                                        resource_id='invalid_label_dep')

        with self.assertRaisesRegex(CloudifyClientError, error_message):
            self.client.deployments.update_labels('invalid_label_dep', [
                    {
                        'csys-obj-parent': 'parent_1'
                    },
                    {
                        'csys-obj-parent': 'notexist'
                    }
                ]
            )

    def test_cyclic_dependencies_between_deployments(self):
        error_message = 'cyclic deployment-labels dependencies.'
        self.put_deployment(deployment_id='deployment_1',
                            blueprint_id='deployment_1')
        self.put_deployment_with_labels(
            [
                {
                    'csys-obj-parent': 'deployment_1'
                }
            ],
            resource_id='deployment_2'
        )
        with self.assertRaisesRegex(CloudifyClientError, error_message):
            self.client.deployments.update_labels('deployment_1', [
                {
                    'csys-obj-parent': 'deployment_2'
                }
            ])

    def test_number_of_direct_services_deployed_inside_environment(self):
        self.put_deployment(deployment_id='env',
                            blueprint_id='env')
        self._create_deployment_objects('env', 'service', 2)
        deployment = self.client.deployments.get(
            'env', all_sub_deployments=False)
        self.assertEqual(deployment.sub_services_count, 2)

    def test_number_of_total_services_deployed_inside_environment(self):
        self.put_deployment(deployment_id='env',
                            blueprint_id='env')
        self._create_deployment_objects('env', 'service', 2)
        self.put_deployment_with_labels(
            [
                {
                    'csys-obj-parent': 'env'
                },
                {
                    'csys-obj-type': 'Environment',
                }
            ],
            resource_id='env_1'
        )

        self._create_deployment_objects('env_1', 'service', 2)
        deployment = self.client.deployments.get('env')
        self.assertEqual(deployment.sub_services_count, 4)
        deployment = self.client.deployments.get('env',
                                                 all_sub_deployments=False)
        self.assertEqual(deployment.sub_services_count, 2)

    def test_number_of_direct_environments_deployed_inside_environment(self):
        self.put_deployment(deployment_id='env',
                            blueprint_id='env')
        self._create_deployment_objects('env', 'environment', 2)
        deployment = self.client.deployments.get(
            'env', all_sub_deployments=False)
        self.assertEqual(deployment.sub_environments_count, 2)

    def test_number_of_total_environments_deployed_inside_environment(self):
        self.put_deployment(deployment_id='env',
                            blueprint_id='env')
        self._create_deployment_objects('env', 'environment', 2)
        self.put_deployment_with_labels(
            [
                {
                    'csys-obj-parent': 'env'
                },
                {
                    'csys-obj-type': 'Environment',
                }
            ],
            resource_id='env_1'
        )

        self._create_deployment_objects('env_1', 'environment', 2)
        deployment = self.client.deployments.get('env')
        self.assertEqual(deployment.sub_environments_count, 5)
        deployment = self.client.deployments.get('env',
                                                 all_sub_deployments=False)
        self.assertEqual(deployment.sub_environments_count, 3)

    def test_create_deployment_labels_dependencies_graph(self):
        self._populate_deployment_labels_dependencies()
        dep_graph = RecursiveDeploymentLabelsDependencies(self.sm)
        dep_graph.create_dependencies_graph()
        self.assertEqual(dep_graph.graph['dep_1'], {'dep_0'})
        self.assertEqual(dep_graph.graph['dep_3'], {'dep_2'})
        self.assertEqual(dep_graph.graph['dep_5'], {'dep_4'})

    def test_add_to_deployment_labels_dependencies_graph(self):
        self._populate_deployment_labels_dependencies()
        dep_graph = RecursiveDeploymentLabelsDependencies(self.sm)
        dep_graph.create_dependencies_graph()
        dep_graph.add_dependency_to_graph('dep_00', 'dep_1')
        dep_graph.add_dependency_to_graph('dep_1', 'dep_6')
        self.assertEqual(dep_graph.graph['dep_1'], {'dep_0', 'dep_00'})
        self.assertEqual(dep_graph.graph['dep_6'], {'dep_1'})

    def test_remove_deployment_labels_dependencies_from_graph(self):
        self._populate_deployment_labels_dependencies()
        dep_graph = RecursiveDeploymentLabelsDependencies(self.sm)
        dep_graph.create_dependencies_graph()
        dep_graph.remove_dependency_from_graph('dep_0', 'dep_1')
        self.assertNotIn('dep_1', dep_graph.graph)

    def test_find_recursive_deployments_from_graph(self):
        self._populate_deployment_labels_dependencies()

        self.client.deployments.update_labels('dep_0', [
                {
                    'csys-obj-parent': 'dep_1'
                }
            ]
        )

        self.put_deployment(deployment_id='dep_11', blueprint_id='dep_11')
        self.put_deployment(deployment_id='dep_12', blueprint_id='dep_12')
        self.put_deployment(deployment_id='dep_13', blueprint_id='dep_13')
        self.put_deployment(deployment_id='dep_14', blueprint_id='dep_14')

        self.client.deployments.update_labels('dep_1', [
                {
                    'csys-obj-parent': 'dep_11'
                }
            ]
        )

        self.client.deployments.update_labels('dep_11', [
                {
                    'csys-obj-parent': 'dep_12'
                }
            ]
        )

        self.client.deployments.update_labels('dep_12', [
                {
                    'csys-obj-parent': 'dep_13'
                }
            ]
        )

        self.client.deployments.update_labels('dep_13', [
                {
                    'csys-obj-parent': 'dep_14'
                }
            ]
        )
        dep_graph = RecursiveDeploymentLabelsDependencies(self.sm)
        dep_graph.create_dependencies_graph()
        targets = dep_graph.find_recursive_deployments('dep_0')
        self.assertEqual(len(targets), 5)
        self.assertIn('dep_1', targets)
        self.assertIn('dep_11', targets)
        self.assertIn('dep_12', targets)
        self.assertIn('dep_13', targets)
        self.assertIn('dep_14', targets)