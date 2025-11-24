-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:55 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_2 = require(game.ReplicatedStorage.Shared.NoteSkinColor)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.Lobby.UI.NoteColorSelectUI.SmallNoteColor)
return {
    ["new"] = function(_, p_u_4, p_u_5, p_u_6, p_u_7) --[[ Name: new ]] --[[ Line: 16 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2 ]]
        local v8 = {}
        local v_u_9 = nil
        v8.cons = function(_) --[[ Name: cons ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_7 ]]
            v_u_9 = p_u_7.Fill
        end;
        v8.calc_display_color = function(_, p10, p11) --[[ Name: calc_display_color ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_4, (copy 3): p_u_6, (ref 4): v_u_3, (ref 5): v_u_2, (copy 6): p_u_5 ]]
            local v_u_12 = v_u_1:new()
            local function f_add_to_dict_combined(p13) --[[ Name: add_to_dict_combined ]] --[[ Line: 29 ]]
                --[[ Upvalues: (copy 1): v_u_12 ]]
                for v14, v15 in p13:key_itr() do
                    if v_u_12:contains(v14) then
                        v_u_12:add(v14, v_u_12:get(v14) + v15)
                    else
                        v_u_12:add(v14, v15)
                    end;
                end;
            end;
            if p11 then
                f_add_to_dict_combined(p_u_4:get_small_note_to_fever_spent_dict())
                f_add_to_dict_combined(p_u_4:get_trackid_fever_to_small_note_to_track_spend_dict():get(p_u_6))
            else
                f_add_to_dict_combined(p_u_4:get_small_note_to_base_spent_dict())
                f_add_to_dict_combined(p_u_4:get_trackid_base_to_small_note_to_track_spend_dict():get(p_u_6))
            end;
            local v16 = 0
            local v17 = 0
            local v18 = 0
            local v19 = 0
            local v20 = 0
            local v21 = 0
            for v22, v23 in v_u_12:key_itr() do
                if v22 == v_u_3.Red then
                    v16 = v16 + v23
                    v17 = math.max(v17, v16)
                elseif v22 == v_u_3.Green then
                    v18 = v18 + v23
                    v17 = math.max(v17, v18)
                elseif v22 == v_u_3.Blue then
                    v19 = v19 + v23
                    v17 = math.max(v17, v19)
                elseif v22 == v_u_3.Orange then
                    v20 = v20 + v23
                elseif v22 == v_u_3.Purple then
                    v21 = v21 + v23
                end;
            end;
            local v24 = v17 + v21 + v20
            local v25 = v16 + v20
            local v26 = v18 + v20
            local v27 = v19 + v20
            local v28, v29, v30
            if v24 > 0 then
                v28 = math.floor(v25 / v24 * 255)
                v29 = math.floor(v26 / v24 * 255)
                v30 = math.floor(v27 / v24 * 255)
            elseif p10 then
                if p11 then
                    v28, v29, v30 = v_u_2:get_default_fever_color():get_rgb()
                else
                    v28, v29, v30 = v_u_2:get_default_base_color():get_rgb()
                end;
            else
                local v31 = p_u_5._player_blob_manager:get_player_blob()
                if p11 then
                    v28, v29, v30 = v_u_2:note_fevercolor_list_from_playerblob(v31):get(p_u_6):get_rgb()
                else
                    v28, v29, v30 = v_u_2:note_basecolor_list_from_playerblob(v31):get(p_u_6):get_rgb()
                end;
            end;
            return v_u_2:new(v28, v29, v30);
        end;
        v8.update_display_color = function(p32) --[[ Name: update_display_color ]] --[[ Line: 102 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_9 ]]
            local v33 = p32:calc_display_color(p_u_4:is_default(), p_u_4:is_fever_mode())
            local _, _, _ = v33:get_rgb()
            v_u_9.ImageColor3 = v33:to_color3()
        end;
        v8:cons()
        return v8;
    end
};
