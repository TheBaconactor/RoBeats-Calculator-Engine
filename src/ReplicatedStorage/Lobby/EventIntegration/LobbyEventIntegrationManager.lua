-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:59 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Lobby.Util.LobbyLocalMode)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v2 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_3 = nil
v2:require_client(function() --[[ Line: 11 ]]
    --[[ Upvalues: (ref 1): v_u_3 ]]
    v_u_3 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
end)
local l_SwallowControlInput_0 = game.ReplicatedStorage.EventIntegration.SwallowControlInput
local l_RaiseExternalBlockInputs_0 = game.ReplicatedStorage.EventIntegration.RaiseExternalBlockInputs
return {
    ["new"] = function(_, _, p_u_4) --[[ Name: new ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): l_RaiseExternalBlockInputs_0, (copy 3): l_SwallowControlInput_0 ]]
        local v5 = {
            ["initialize_npcs"] = function(_) end,
            ["is_event_integration_hud_active"] = function(_) --[[ Name: is_event_integration_hud_active ]] --[[ Line: 67 ]]
                return false;
            end,
            ["get_hud_button_assetid"] = function(_) --[[ Name: get_hud_button_assetid ]] --[[ Line: 71 ]]
                return "";
            end,
            ["on_hud_button_pressed"] = function(_) end
        }
        local v_u_6 = v_u_1:new()
        local function _() end;
        v5.update = function(_, _) --[[ Name: update ]] --[[ Line: 78 ]]
            --[[ Upvalues: (ref 1): l_RaiseExternalBlockInputs_0, (copy 2): p_u_4 ]]
            if l_RaiseExternalBlockInputs_0.Value == true then
                p_u_4._input:set_has_frame_focused_element(true)
            end;
        end;
        v5.post_update = function(_, _) --[[ Name: post_update ]] --[[ Line: 95 ]]
            --[[ Upvalues: (ref 1): l_SwallowControlInput_0, (copy 2): p_u_4 ]]
            l_SwallowControlInput_0.Value = p_u_4._ui_manager:swallow_control_input()
        end;
        v5.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 103 ]]
            --[[ Upvalues: (copy 1): v_u_6 ]]
            for _, v7 in v_u_6:key_itr() do
                v7:Disconnect()
            end;
            v_u_6:clear()
        end;
        return v5;
    end
};
