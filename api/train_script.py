"""Train scripting language interpreter for automated sequences."""
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScriptCommand:
    """Represents a parsed script command."""
    command: str
    args: List[str]
    line_number: int


class TrainScriptError(Exception):
    """Exception raised for script execution errors."""
    pass


class TrainScriptInterpreter:
    """
    Interpreter for train control scripts.

    Supported commands:
    - speed <-100 to 100>   : Set train speed
                              Negative=force reverse, Positive=use current direction, 0=stop
                              Example: speed -50 OR (reverse + speed 50) both give reverse at 50
    - forward               : Set direction forward
    - reverse               : Set direction reverse
    - toggle                : Toggle direction
    - horn                  : Blow horn
    - bell on|off           : Control bell
    - lights on|off         : Control lights
    - wait <seconds>        : Wait/delay
    - repeat <n> times      : Start repeat loop
    - end                   : End repeat loop
    - # comment             : Comment (ignored)

    Example script:
        # Simple train sequence
        speed 0
        bell on
        lights on
        wait 2
        speed 15
        forward
        wait 5
        horn
        wait 1
        speed 0
        bell off
        lights off
    """

    def __init__(self, train_controller):
        """
        Initialize interpreter.

        Args:
            train_controller: TrainController instance for executing commands
        """
        self.train_controller = train_controller
        self.is_running = False
        self.should_stop = False

    def parse_script(self, script: str) -> List[ScriptCommand]:
        """
        Parse script into commands.

        Args:
            script: Script text

        Returns:
            List of parsed commands

        Raises:
            TrainScriptError: If script has syntax errors
        """
        commands = []
        lines = script.strip().split('\n')

        for line_num, line in enumerate(lines, 1):
            # Remove leading/trailing whitespace
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Parse command and arguments
            parts = line.split()
            if not parts:
                continue

            command = parts[0].lower()
            args = parts[1:]

            # Validate command syntax
            self._validate_command(command, args, line_num)

            commands.append(ScriptCommand(
                command=command,
                args=args,
                line_number=line_num
            ))

        # Validate loop structure
        self._validate_loops(commands)

        return commands

    def _validate_command(self, command: str, args: List[str], line_num: int):
        """Validate command syntax."""
        valid_commands = {
            'speed': 1,      # speed <-100 to 100>
            'forward': 0,    # forward
            'reverse': 0,    # reverse
            'toggle': 0,     # toggle
            'horn': 0,       # horn
            'bell': 1,       # bell on|off
            'lights': 1,     # lights on|off
            'wait': 1,       # wait <seconds>
            'repeat': 2,     # repeat <n> times
            'end': 0,        # end
        }

        if command not in valid_commands:
            raise TrainScriptError(
                f"Line {line_num}: Unknown command '{command}'"
            )

        expected_args = valid_commands[command]
        if len(args) != expected_args:
            raise TrainScriptError(
                f"Line {line_num}: Command '{command}' expects {expected_args} argument(s), got {len(args)}"
            )

        # Validate specific argument values
        if command == 'speed':
            try:
                speed = int(args[0])
                if not -100 <= speed <= 100:
                    raise ValueError()
            except ValueError:
                raise TrainScriptError(
                    f"Line {line_num}: Speed must be integer -100 to 100, got '{args[0]}'"
                )

        elif command == 'bell':
            if args[0].lower() not in ['on', 'off']:
                raise TrainScriptError(
                    f"Line {line_num}: Bell argument must be 'on' or 'off', got '{args[0]}'"
                )

        elif command == 'lights':
            if args[0].lower() not in ['on', 'off']:
                raise TrainScriptError(
                    f"Line {line_num}: Lights argument must be 'on' or 'off', got '{args[0]}'"
                )

        elif command == 'wait':
            try:
                wait_time = float(args[0])
                if wait_time < 0:
                    raise ValueError()
            except ValueError:
                raise TrainScriptError(
                    f"Line {line_num}: Wait time must be positive number, got '{args[0]}'"
                )

        elif command == 'repeat':
            try:
                times = int(args[0])
                if times < 1:
                    raise ValueError()
            except ValueError:
                raise TrainScriptError(
                    f"Line {line_num}: Repeat count must be positive integer, got '{args[0]}'"
                )

            if args[1].lower() != 'times':
                raise TrainScriptError(
                    f"Line {line_num}: Expected 'times' keyword, got '{args[1]}'"
                )

    def _validate_loops(self, commands: List[ScriptCommand]):
        """Validate loop structure (matching repeat/end)."""
        stack = []
        for cmd in commands:
            if cmd.command == 'repeat':
                stack.append(cmd.line_number)
            elif cmd.command == 'end':
                if not stack:
                    raise TrainScriptError(
                        f"Line {cmd.line_number}: 'end' without matching 'repeat'"
                    )
                stack.pop()

        if stack:
            raise TrainScriptError(
                f"Line {stack[-1]}: 'repeat' without matching 'end'"
            )

    async def execute_script(self, script: str) -> Dict[str, Any]:
        """
        Execute a train control script.

        Args:
            script: Script text to execute

        Returns:
            Execution result dictionary

        Raises:
            TrainScriptError: If script execution fails
        """
        if self.is_running:
            raise TrainScriptError("Script is already running")

        try:
            self.is_running = True
            self.should_stop = False

            # Parse script
            commands = self.parse_script(script)

            # Execute commands
            await self._execute_commands(commands)

            return {
                "success": True,
                "message": "Script completed successfully",
                "commands_executed": len(commands)
            }

        except TrainScriptError as e:
            logger.error(f"Script error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error executing script: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
        finally:
            self.is_running = False

    async def _execute_commands(self, commands: List[ScriptCommand], start_idx: int = 0, end_idx: Optional[int] = None):
        """Execute a sequence of commands."""
        if end_idx is None:
            end_idx = len(commands)

        i = start_idx
        while i < end_idx:
            if self.should_stop:
                logger.info("Script execution stopped")
                break

            cmd = commands[i]

            try:
                if cmd.command == 'repeat':
                    # Find matching end
                    loop_end = self._find_loop_end(commands, i)
                    times = int(cmd.args[0])

                    # Execute loop body
                    for _ in range(times):
                        if self.should_stop:
                            break
                        await self._execute_commands(commands, i + 1, loop_end)

                    i = loop_end  # Skip to end

                elif cmd.command == 'end':
                    # Should be handled by repeat logic
                    pass

                else:
                    # Execute single command
                    await self._execute_single_command(cmd)

            except Exception as e:
                raise TrainScriptError(
                    f"Line {cmd.line_number}: Error executing '{cmd.command}': {str(e)}"
                )

            i += 1

    def _find_loop_end(self, commands: List[ScriptCommand], repeat_idx: int) -> int:
        """Find the matching 'end' for a 'repeat' command."""
        depth = 0
        for i in range(repeat_idx, len(commands)):
            if commands[i].command == 'repeat':
                depth += 1
            elif commands[i].command == 'end':
                depth -= 1
                if depth == 0:
                    return i
        return len(commands)

    async def _execute_single_command(self, cmd: ScriptCommand):
        """Execute a single train command."""
        command = cmd.command
        args = cmd.args

        logger.debug(f"Executing: {command} {' '.join(args)}")

        if command == 'speed':
            speed = int(args[0])
            result = await self.train_controller.set_speed(speed)
            if not result.get("success", False):
                raise Exception(result.get("message", "Speed command failed"))

        elif command == 'forward':
            result = await self.train_controller.set_direction('forward')
            if not result.get("success", False):
                raise Exception(result.get("message", "Direction command failed"))

        elif command == 'reverse':
            result = await self.train_controller.set_direction('reverse')
            if not result.get("success", False):
                raise Exception(result.get("message", "Direction command failed"))

        elif command == 'toggle':
            result = await self.train_controller.set_direction('toggle')
            if not result.get("success", False):
                raise Exception(result.get("message", "Direction command failed"))

        elif command == 'horn':
            result = await self.train_controller.blow_horn()
            if not result.get("success", False):
                raise Exception(result.get("message", "Horn command failed"))

        elif command == 'bell':
            state = args[0].lower() == 'on'
            result = await self.train_controller.ring_bell(state)
            if not result.get("success", False):
                raise Exception(result.get("message", "Bell command failed"))

        elif command == 'lights':
            state = args[0].lower() == 'on'
            result = await self.train_controller.set_lights(state)
            if not result.get("success", False):
                raise Exception(result.get("message", "Lights command failed"))

        elif command == 'wait':
            wait_time = float(args[0])
            # Check for stop signal periodically during wait
            elapsed = 0
            interval = 0.1
            while elapsed < wait_time and not self.should_stop:
                await asyncio.sleep(min(interval, wait_time - elapsed))
                elapsed += interval

    def stop(self):
        """Stop script execution."""
        self.should_stop = True
        logger.info("Script stop requested")
