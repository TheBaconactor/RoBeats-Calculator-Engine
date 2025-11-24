-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:26 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
local v_u_2 = require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.LocalShared.CharacterCulling)
local v_u_4 = require(game.ReplicatedStorage.Local.LocalCharacter)
return {
    ["new"] = function(_, p_u_5) --[[ Name: new ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_3 ]]
        local v6 = {}
        local v_u_7 = v_u_1:new()
        v6.create_local_characters = function(_, p8) --[[ Name: create_local_characters ]] --[[ Line: 19 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_7 ]]
            for v9, v10 in p8._players._slots:key_itr() do
                v_u_7:add(v10._id, (v_u_4:new(p8, v10._id, v9, v10)))
            end;
        end;
        v6.update = function(_, p11, p12) --[[ Name: update ]] --[[ Line: 26 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            for v13, v14 in v_u_7:key_itr() do
                if p12._players:contains_player_of_id(v13) == false then
                    v14:teardown()
                    v_u_7:remove(v13)
                else
                    v14:update(p11, p12)
                end;
            end;
        end;
        v6.set_paused = function(_, p15) --[[ Name: set_paused ]] --[[ Line: 37 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            for _, v16 in v_u_7:key_itr() do
                v16:set_paused(p15)
            end;
        end;
        v6.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 43 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            for _, v17 in v_u_7:key_itr() do
                v17:teardown()
            end;
            v_u_7:clear()
        end;
        v6.get_character_location_for_slot = function(_, p18) --[[ Name: get_character_location_for_slot ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_5 ]]
            local v19 = v_u_2:slot_to_character_cframe(p18)
            local l_Unit_0 = (v_u_2:slot_to_world_position(p18) - v_u_2:get_world_center_position()).Unit
            local v20 = Vector3.new(0, 1, 0)
            local v21, v22, v23, v24 = p_u_5._world_effect_manager:process_character_location_for_slot(v19, l_Unit_0, v20:Cross(l_Unit_0), v20)
            local v25
            if p_u_5:show_fullscreen_mobile_ui() then
                v25 = v21 + v23 * 1 + v22 * -4.25
            else
                v25 = v21
            end;
            return v25, v21, v22, v23, v24;
        end;
        v6.should_show_characters = function(_) --[[ Name: should_show_characters ]] --[[ Line: 67 ]]
            --[[ Upvalues: (copy 1): p_u_5, (ref 2): v_u_3 ]]
            return p_u_5._player_settings_manager:get_key(v_u_3.Key.GameShowCharacters);
        end;
        v6.update_show_characters = function(p26) --[[ Name: update_show_characters ]] --[[ Line: 71 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            for _, v27 in v_u_7:key_itr() do
                v27:set_visible(p26:should_show_characters())
            end;
        end;
        return v6;
    end
};
