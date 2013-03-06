/*******************************************************************************
 * Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 ******************************************************************************/
package org.cloudifysource.cosmo.mock;

import org.cloudifysource.cosmo.ImpersonatingTaskConsumer;
import org.cloudifysource.cosmo.TaskConsumerState;
import org.cloudifysource.cosmo.TaskConsumerStateHolder;
import org.cloudifysource.cosmo.TaskConsumerStateModifier;
import org.cloudifysource.cosmo.agent.state.AgentState;
import org.cloudifysource.cosmo.agent.tasks.MachineLifecycleTask;
import org.cloudifysource.cosmo.mock.ssh.MockSSHAgent;
import org.cloudifysource.cosmo.service.lifecycle.LifecycleState;

import java.net.URI;

/**
 * A mock that simulates starting a new machine and a new agent.
 * @author itaif
 * @since 0.1
 */
public class MockMachineProvisioner {

    private static final boolean USE_SSH = false;

    private final TaskConsumerState state = new TaskConsumerState();
    private final TaskConsumerRegistrar taskConsumerRegistrar;

    public MockMachineProvisioner(TaskConsumerRegistrar taskConsumerRegistrar) {
        this.taskConsumerRegistrar = taskConsumerRegistrar;
    }

    @ImpersonatingTaskConsumer
    public void machineLifecycle(MachineLifecycleTask task,
                                 TaskConsumerStateModifier<AgentState> impersonatedStateModifier) {

        final AgentState agentState = impersonatedStateModifier.get();
        final LifecycleState lifecycleState = task.getLifecycleState();
        final URI agentId = task.getStateId();
        if (lifecycleState.equals(agentState.getMachineReachableLifecycle())) {
            machineReachable(agentState, agentId);
        } else if (lifecycleState.equals(agentState.getMachineStartedLifecycle())) {
            machineStarted(agentState);
        } else if (lifecycleState.equals(agentState.getMachineTerminatedLifecycle())) {
            machineTerminated(agentState, agentId);
        }

        agentState.getStateMachine().setCurrentState(lifecycleState);
        impersonatedStateModifier.put(agentState);
    }

    private void machineTerminated(AgentState machineState, URI agentId) {
        if (!machineState.isMachineTerminatedLifecycle()) {
            taskConsumerRegistrar.unregisterTaskConsumer(agentId);
        }
    }

    private void machineStarted(AgentState machineState) {
        if (!machineState.isMachineStartedLifecycle()) {
            machineState.incrementNumberOfMachineStarts();
            machineState.resetNumberOfAgentStarts();
        }
    }

    private void machineReachable(AgentState machineState, URI agentId) {
        if (!machineState.isMachineReachableLifecycle()) {
            machineState.incrementNumberOfAgentStarts();
            Object newAgent;
            if (USE_SSH) {
                newAgent = MockSSHAgent.newAgentOnCleanMachine(machineState);
            } else {
                newAgent = MockAgent.newAgentOnCleanMachine(machineState);
            }
            taskConsumerRegistrar.registerTaskConsumer(newAgent, agentId);
        }
    }

    @TaskConsumerStateHolder
    public TaskConsumerState getState() {
        return state;
    }

}
