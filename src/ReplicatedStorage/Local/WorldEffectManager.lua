-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:24 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Effects.NoteBurstShineEffect)
local v_u_4 = require(game.ReplicatedStorage.Shared.NoteResult)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.ModelLoadDB)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.EventString)
require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_8 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
local v_u_9 = require(game.ReplicatedStorage.Local.GameLocalMode)
local v_u_10 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
return {
    ["new"] = function(_, _) --[[ Name: new ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_6, (copy 3): v_u_1, (copy 4): v_u_5, (copy 5): v_u_8, (copy 6): v_u_10, (copy 7): v_u_9, (copy 8): v_u_4, (copy 9): v_u_7, (copy 10): v_u_3 ]]
        local v_u_11 = {
            ["post_update"] = function(_, _, _) end
        }
        local v_u_12 = nil
        local v_u_13 = false
        v_u_11.is_game_stage_loaded = function(_) --[[ Name: is_game_stage_loaded ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            return v_u_13;
        end;
        local function _() end;
        local function f_post_loaded_setup_game_stage_info(p_u_14) --[[ Name: post_loaded_setup_game_stage_info ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_12, (ref 3): v_u_6, (ref 4): v_u_1, (copy 5): v_u_11 ]]
            local v15, v16 = v_u_2:try(function() --[[ Line: 34 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_14 ]]
                v_u_12:setup_stage(p_u_14)
            end)
            if v15 ~= true then
                v_u_6:warnf("post_loaded_setup_game_stage_info(%s)[%s]", v16.Error, v16.StackTrace)
            end;
            if p_u_14._characters:should_show_characters() then
                for v17 = v_u_1.SLOT_MIN, v_u_1.SLOT_MAX do
                    if p_u_14._players._slots:contains(v17) then
                        v_u_11:game_create_shine_for_slot_at_cframe(p_u_14, v17, CFrame.new(p_u_14._characters:get_character_location_for_slot(v17).p))
                    end;
                end;
            end;
        end;
        v_u_11.load_game_stage_info = function(_, p_u_18, p_u_19) --[[ Name: load_game_stage_info ]] --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_5, (ref 3): v_u_12, (ref 4): v_u_8, (ref 5): v_u_6, (ref 6): v_u_13, (ref 7): v_u_10, (ref 8): v_u_9, (copy 9): f_post_loaded_setup_game_stage_info ]]
            if p_u_18._players._slots:contains(p_u_18:get_local_game_slot()) then
                local v20 = p_u_18._players._slots:get(p_u_18:get_local_game_slot())
                if v_u_2:is_dev_build() and v_u_5.UseDebugGameStage == true then
                    v_u_12 = v_u_8:singleton():get_stage_info_for_id(v_u_5.DebugGameStageID)
                else
                    v_u_12 = v_u_8:singleton():get_stage_info_for_id(v20._stage_id)
                end;
            end;
            if v_u_12 == nil then
                v_u_6:warnf("WorldEffectManager:setup_world no _game_stage_info, using default game stage")
                v_u_12 = v_u_8:singleton():get_default_game_stage_info()
            end;
            v_u_13 = false
            local v_u_21 = v_u_12
            v_u_10:singleton():get_error_id_set():clear()
            v_u_21:load_stage(function() --[[ Line: 73 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_21, (ref 3): v_u_6, (copy 4): p_u_18, (ref 5): v_u_9, (ref 6): v_u_10, (ref 7): v_u_8, (ref 8): v_u_13, (ref 9): f_post_loaded_setup_game_stage_info, (copy 10): p_u_19 ]]
                if v_u_12 ~= v_u_21 then
                    return v_u_6:warnf("WorldEffectManager:load_game_stage_info load_stage but current game_stage_info not matching loading_game_stage_info");
                end;
                if p_u_18:get_current_mode() == v_u_9.DoRemove then
                    return v_u_6:warnf("WorldEffectManager:load_game_stage_info load_stage but game:get_current_mode() is doremove");
                end;
                if v_u_10:singleton():get_error_id_set():count() > 0 then
                    v_u_12 = v_u_8:singleton():get_default_game_stage_info()
                    v_u_12:load_stage_immediate()
                    v_u_6:warnf("load_game_stage_info ModelLoadDB error_id_set(%d), using default game stage load_stage_immediate", v_u_10:singleton():get_error_id_set():count())
                    v_u_10:singleton():get_error_id_set():clear()
                end;
                v_u_13 = true
                f_post_loaded_setup_game_stage_info(p_u_18)
                p_u_19()
            end)
        end;
        v_u_11.force_load_default_stage = function(_, p22) --[[ Name: force_load_default_stage ]] --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_6, (ref 3): v_u_12, (ref 4): v_u_8, (copy 5): f_post_loaded_setup_game_stage_info ]]
            if v_u_13 == true then
                return v_u_6:warnf("WorldEffectManager:force_load_default_stage when _is_game_stage_loaded");
            end;
            v_u_12 = v_u_8:singleton():get_default_game_stage_info()
            v_u_12:load_stage_immediate()
            v_u_13 = true
            f_post_loaded_setup_game_stage_info(p22)
        end;
        v_u_11.teardown = function(_, p_u_23) --[[ Name: teardown ]] --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_6, (ref 3): v_u_2, (ref 4): v_u_12 ]]
            if v_u_13 ~= true then
                return v_u_6:warnf("WorldEffectManager:teardown when _is_game_stage_loaded false");
            end;
            local v24, v25 = v_u_2:try(function() --[[ Line: 104 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_23 ]]
                v_u_12:teardown_stage(p_u_23)
            end)
            if v24 ~= true then
                v_u_6:warnf("teardown(%s)[%s]", v25.Error, v25.StackTrace)
            end;
        end;
        v_u_11.process_character_location_for_slot = function(_, p26, p27, p28, p29) --[[ Name: process_character_location_for_slot ]] --[[ Line: 112 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_6, (ref 3): v_u_12 ]]
            if v_u_13 == true then
                local v30, v31, v32, v33 = v_u_12:process_character_location_for_slot(p26, p27, p28, p29)
                return v30, v31, v32, v33;
            else
                v_u_6:warnf("WorldEffectManager:process_character_location_for_slot when _is_game_stage_loaded false")
                return p26, p27, p28, p29;
            end;
        end;
        v_u_11.game_create_shine_for_slot_at_cframe = function(_, p_u_34, p_u_35, p_u_36) --[[ Name: game_create_shine_for_slot_at_cframe ]] --[[ Line: 122 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_6, (ref 3): v_u_2, (ref 4): v_u_12 ]]
            if v_u_13 ~= true then
                return v_u_6:warnf("WorldEffectManager:game_create_shine_for_slot_at_cframe when _is_game_stage_loaded false");
            end;
            local v37, v38 = v_u_2:try(function() --[[ Line: 125 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_34, (copy 3): p_u_35, (copy 4): p_u_36 ]]
                v_u_12:create_shine_for_slot_at_cframe(p_u_34, p_u_35, p_u_36)
            end)
            if v37 ~= true then
                v_u_6:warnf("create_shine_for_slot_at_cframe(%s)[%s]", v38.Error, v38.StackTrace)
            end;
        end;
        v_u_11.on_switch_focus_slot = function(_, p_u_39) --[[ Name: on_switch_focus_slot ]] --[[ Line: 133 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_6, (ref 3): v_u_2, (ref 4): v_u_12 ]]
            if v_u_13 ~= true then
                return v_u_6:warnf("WorldEffectManager:on_switch_focus_slot when _is_game_stage_loaded false");
            end;
            local v40, v41 = v_u_2:try(function() --[[ Line: 138 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_39 ]]
                v_u_12:on_switch_focus_slot(p_u_39)
            end)
            if v40 ~= true then
                v_u_6:warnf("on_switch_focus_slot(%s)[%s]", v41.Error, v41.StackTrace)
            end;
        end;
        v_u_11.create_trigger_button_asset = function(_, p_u_42, p_u_43, p_u_44) --[[ Name: create_trigger_button_asset ]] --[[ Line: 146 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_6, (ref 3): v_u_8, (ref 4): v_u_2, (ref 5): v_u_12 ]]
            if v_u_13 ~= true then
                v_u_6:warnf("WorldEffectManager:create_trigger_button_asset when _is_game_stage_loaded false")
                return v_u_8:singleton():get_default_game_stage_info():create_trigger_button_asset(p_u_42, p_u_43, p_u_44);
            end;
            local v_u_45 = nil
            local v46, v47 = v_u_2:try(function() --[[ Line: 153 ]]
                --[[ Upvalues: (ref 1): v_u_45, (ref 2): v_u_12, (copy 3): p_u_42, (copy 4): p_u_43, (copy 5): p_u_44 ]]
                v_u_45 = v_u_12:create_trigger_button_asset(p_u_42, p_u_43, p_u_44)
            end)
            local v48
            if v46 == true then
                v48 = v_u_45
            else
                v_u_6:warnf("create_trigger_button_asset(%s)[%s]", v47.Error, v47.StackTrace)
                v_u_45 = v_u_8:singleton():get_default_game_stage_info():create_trigger_button_asset(p_u_42, p_u_43, p_u_44)
                v48 = v_u_45
            end;
            return v48;
        end;
        local v_u_49 = false
        v_u_11.update = function(_, p_u_50, p_u_51) --[[ Name: update ]] --[[ Line: 164 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_6, (ref 3): v_u_12, (ref 4): v_u_49 ]]
            if v_u_13 ~= true then
                return v_u_6:warnf("WorldEffectManager:update when _is_game_stage_loaded false");
            end;
            local v52, v53 = pcall(function() --[[ Line: 169 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_50, (copy 3): p_u_51 ]]
                v_u_12:game_update(p_u_50, p_u_51)
            end)
            if v52 ~= true and v_u_49 == false then
                v_u_6:warnf("update(%s)", v53)
                v_u_49 = true
            end;
        end;
        v_u_11.notify_hit = function(_, p54, p55, p56, p57) --[[ Name: notify_hit ]] --[[ Line: 183 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_7, (ref 3): v_u_3 ]]
            if p56 == p54:get_local_game_slot() then
                if p54:es_gamelocal_get_scoremanager():display_powerbar_active() then
                    if p55 ~= v_u_4.NoteResult_Miss then
                        local v58 = p54:es_gamelocal_get_tracksystems():get(p56)
                        if v58 and v58:get_active_note_display_mode() == v_u_7.Default then
                            p54._effects:add_effect(v_u_3:new(p54, p54:es_gamelocal_tracksystem_of_index(p56):es_get_track(p57):get_end_position(), p56))
                        end;
                    end;
                else
                    return;
                end;
            else
                return;
            end;
        end;
        v_u_11.notify_hold_tick = function(_, p59, p60, p61) --[[ Name: notify_hold_tick ]] --[[ Line: 199 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            if p60 == p59:get_local_game_slot() then
                if p59:es_gamelocal_get_scoremanager():display_powerbar_active() then
                    p59._effects:add_effect(v_u_3:new(p59, p59:es_gamelocal_tracksystem_of_index(p60):es_get_track(p61):get_end_position(), p60))
                end;
            else
                return;
            end;
        end;
        v_u_11.should_do_game_start_zoom_in_effect = function(_) --[[ Name: should_do_game_start_zoom_in_effect ]] --[[ Line: 209 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_6 ]]
            if v_u_12 ~= nil then
                return v_u_12:should_do_game_start_zoom_in_effect();
            end;
            v_u_6:warnf("WorldEffectManager:should_do_game_start_zoom_in_effect called when _game_stage_info not setup")
            return true;
        end;
        local v_u_62 = nil
        v_u_11.game_camera_transition = function(_, p63) --[[ Name: game_camera_transition ]] --[[ Line: 219 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_62 ]]
            if v_u_12 == nil then
                return;
            elseif p63 ~= v_u_62 then
                v_u_62 = p63
                v_u_12:game_camera_transition(p63)
            end;
        end;
        return v_u_11;
    end
};
