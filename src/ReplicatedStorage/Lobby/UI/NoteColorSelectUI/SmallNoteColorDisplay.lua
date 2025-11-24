-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:55 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_2 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.Shared.NoteSkinColor)
local v_u_4 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = require(game.ReplicatedStorage.Lobby.UI.NoteColorSelectUI.SmallNoteColor)
return {
    ["new"] = function(_, p_u_6, p_u_7, p_u_8, p_u_9, p_u_10, p_u_11) --[[ Name: new ]] --[[ Line: 16 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_5, (copy 3): v_u_2, (copy 4): v_u_1, (copy 5): v_u_3 ]]
        local v12 = {}
        v_u_4:is_true(v_u_5.SMALL_NOTE_COLOR_TO_MATERIAL_ID:contains(p_u_8))
        local l__spui_0 = p_u_7._spui
        local v_u_13 = nil
        local v_u_14 = nil
        local v_u_15 = nil
        local v_u_16 = nil
        v12.cons = function(_) --[[ Name: cons ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_9, (ref 3): v_u_14, (ref 4): v_u_15, (copy 5): p_u_6, (copy 6): p_u_7, (ref 7): v_u_2, (ref 8): v_u_1, (copy 9): p_u_10, (copy 10): l__spui_0, (ref 11): v_u_3, (copy 12): p_u_8, (ref 13): v_u_16, (copy 14): p_u_11 ]]
            v_u_13 = p_u_9.Notification
            v_u_14 = v_u_13.Display
            v_u_15 = p_u_6:add_cycle_element(p_u_7, 1, v_u_2:new(v_u_1:new(p_u_6, p_u_6:get_obj().PrimaryPart, p_u_10), l__spui_0, function() --[[ Line: 33 ]]
                --[[ Upvalues: (ref 1): p_u_7, (ref 2): v_u_3, (ref 3): p_u_6, (ref 4): p_u_8 ]]
                p_u_7._sfx_manager:play_sfx(v_u_3.SFX_MENU_OPEN)
                p_u_6:note_spend_changed(p_u_8, 1)
            end))
            v_u_16 = p_u_6:add_cycle_element(p_u_7, 1, v_u_2:new(v_u_1:new(p_u_6, p_u_6:get_obj().PrimaryPart, p_u_11), l__spui_0, function() --[[ Line: 41 ]]
                --[[ Upvalues: (ref 1): p_u_7, (ref 2): v_u_3, (ref 3): p_u_6, (ref 4): p_u_8 ]]
                p_u_7._sfx_manager:play_sfx(v_u_3.SFX_MENU_OPEN)
                p_u_6:note_spend_changed(p_u_8, -1)
            end))
        end;
        local function _() --[[ Name: get_max_used_notes ]] --[[ Line: 48 ]]
            return 99;
        end;
        local function _(p17) --[[ Name: smnote_dict_count_gt_zero ]] --[[ Line: 54 ]]
            --[[ Upvalues: (copy 1): p_u_8 ]]
            if p17:contains(p_u_8) == true then
                return p17:get(p_u_8) > 0;
            else
                return false;
            end;
        end;
        v12.set_spent_count = function(_, p18) --[[ Name: set_spent_count ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_14, (ref 3): v_u_15, (copy 4): p_u_6, (copy 5): p_u_8, (ref 6): v_u_16 ]]
            if p18 > 0 then
                v_u_13.Visible = true
                v_u_14.Text = string.format("%d", p18)
            else
                v_u_13.Visible = false
            end;
            v_u_15:set_visible(p18 < 99)
            local v19 = false
            if p_u_6:is_basecolor_mode() then
                if p_u_6:has_focused_track() then
                    local v20 = p_u_6:get_trackid_base_to_small_note_to_track_spend_dict():get(p_u_6:get_focused_track())
                    if v20:contains(p_u_8) == true then
                        v19 = v20:get(p_u_8) > 0
                    else
                        v19 = false
                    end;
                else
                    local v21 = p_u_6:get_small_note_to_base_spent_dict()
                    if v21:contains(p_u_8) == true then
                        v19 = v21:get(p_u_8) > 0
                    else
                        v19 = false
                    end;
                end;
            elseif p_u_6:is_fever_mode() then
                if p_u_6:has_focused_track() then
                    local v22 = p_u_6:get_trackid_fever_to_small_note_to_track_spend_dict():get(p_u_6:get_focused_track())
                    if v22:contains(p_u_8) == true then
                        v19 = v22:get(p_u_8) > 0
                    else
                        v19 = false
                    end;
                else
                    local v23 = p_u_6:get_small_note_to_fever_spent_dict()
                    if v23:contains(p_u_8) == true then
                        v19 = v23:get(p_u_8) > 0
                    else
                        v19 = false
                    end;
                end;
            end;
            v_u_16:set_visible(v19)
        end;
        v12:cons()
        return v12;
    end
};
