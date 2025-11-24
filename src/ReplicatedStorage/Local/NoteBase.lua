-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:26 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.NoteResult)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_2 = require(game.ReplicatedStorage.Shared.NoteSkinColor)
return {
    ["NoteBase"] = function(_, p_u_3) --[[ Name: NoteBase ]] --[[ Line: 8 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        local v4 = {
            ["update"] = function(_, _, _) --[[ Name: update ]] --[[ Line: 14 ]]
                error("NoteBase must implement")
            end,
            ["should_remove"] = function(_, _) --[[ Name: should_remove ]] --[[ Line: 15 ]]
                error("NoteBase must implement")
                return false;
            end,
            ["do_remove"] = function(_, _) --[[ Name: do_remove ]] --[[ Line: 16 ]]
                error("NoteBase must implement")
            end,
            ["get_state"] = function(_) --[[ Name: get_state ]] --[[ Line: 18 ]]
                return -1;
            end,
            ["es_note_on_hit"] = function(_, _, _, _, _) --[[ Name: es_note_on_hit ]] --[[ Line: 22 ]]
                error("NoteBase must implement")
            end,
            ["es_note_on_release"] = function(_, _, _, _, _) --[[ Name: es_note_on_release ]] --[[ Line: 28 ]]
                error("NoteBase must implement")
            end,
            ["get_track_index"] = function(_) --[[ Name: get_track_index ]] --[[ Line: 32 ]]
                error("NoteBase must implement")
                return 0;
            end,
            ["get_base_transparency"] = function(_, _) --[[ Name: get_base_transparency ]] --[[ Line: 62 ]]
                return 0.15;
            end,
            ["update_note_display_mode"] = function(_) --[[ Name: update_note_display_mode ]] --[[ Line: 66 ]]
                warn("NoteBase update_note_display_mode not implemented")
            end
        }
        v4.get_note_index = function(_) --[[ Name: get_note_index ]] --[[ Line: 11 ]]
            --[[ Upvalues: (ref 1): p_u_3 ]]
            return p_u_3;
        end;
        v4.set_note_index = function(_, p5) --[[ Name: set_note_index ]] --[[ Line: 12 ]]
            --[[ Upvalues: (ref 1): p_u_3 ]]
            p_u_3 = p5
        end;
        v4.es_note_test_hit = function(_, _, _) --[[ Name: es_note_test_hit ]] --[[ Line: 19 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            return false, v_u_1.NoteResult_Miss, 0;
        end;
        v4.es_note_test_release = function(_, _, _) --[[ Name: es_note_test_release ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            return false, v_u_1.NoteResult_Miss, 0;
        end;
        local v_u_6 = nil
        local v_u_7 = nil
        v4.set_note_colors = function(_, p8, p9) --[[ Name: set_note_colors ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7 ]]
            v_u_6 = p8
            v_u_7 = p9
        end;
        v4.reset_note_colors = function(_) --[[ Name: reset_note_colors ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7 ]]
            v_u_6 = nil
            v_u_7 = nil
        end;
        v4.color3_for_slot = function(_, _, p10) --[[ Name: color3_for_slot ]] --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_2, (ref 3): v_u_6 ]]
            if p10 then
                if v_u_7 == nil then
                    return v_u_2:get_default_fever_color():to_color3();
                else
                    return v_u_7:to_color3();
                end;
            elseif v_u_6 == nil then
                return v_u_2:get_default_base_color():to_color3();
            else
                return v_u_6:to_color3();
            end;
        end;
        return v4;
    end
};
