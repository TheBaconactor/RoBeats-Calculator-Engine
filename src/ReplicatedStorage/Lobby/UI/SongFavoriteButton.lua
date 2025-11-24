-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:50 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_2 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
return {
    ["new"] = function(_, p_u_6, p_u_7, p_u_8, p_u_9) --[[ Name: new ]] --[[ Line: 10 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_3, (copy 5): v_u_5 ]]
        local v_u_10 = {}
        local v_u_11 = v_u_2:invalid_songkey()
        v_u_10.set_default_selected_songkey = function(p12, p13) --[[ Name: set_default_selected_songkey ]] --[[ Line: 14 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11 = p13
            p12:refresh_display()
            return p12;
        end;
        local function v_u_14() --[[ Line: 19 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11;
        end;
        v_u_10.set_fn_get_selected_songkey = function(p15, p16) --[[ Name: set_fn_get_selected_songkey ]] --[[ Line: 20 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            v_u_14 = p16
            p15:refresh_display()
            return p15;
        end;
        local function v_u_17() end;
        v_u_10.set_fn_on_favorite_updated = function(p18, p19) --[[ Name: set_fn_on_favorite_updated ]] --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17 = p19
            return p18;
        end;
        local v_u_20 = nil
        v_u_10.get_button = function(_) --[[ Name: get_button ]] --[[ Line: 29 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_20, (copy 2): p_u_7, (copy 3): p_u_6, (ref 4): v_u_1, (copy 5): p_u_8, (ref 6): v_u_14, (ref 7): v_u_2, (ref 8): v_u_4, (ref 9): v_u_3, (copy 10): v_u_10, (ref 11): v_u_17 ]]
            v_u_20 = p_u_7:add_cycle_element(p_u_6, 1, v_u_1:new(p_u_8, p_u_6._spui, function() --[[ Line: 35 ]]
                --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_2, (ref 3): v_u_4, (ref 4): p_u_6, (ref 5): v_u_3, (ref 6): v_u_10, (ref 7): v_u_17 ]]
                local v21 = v_u_14()
                if v_u_2:singleton():contains_key(v21) ~= true then
                    return v_u_4:warnf("favoritebutton press invalid songkey");
                end;
                p_u_6._sfx_manager:play_sfx(v_u_3.SFX_BUTTONPRESS)
                p_u_6._player_blob_manager:add_song_to_favorites(v21, function() --[[ Line: 40 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_17 ]]
                    v_u_10:refresh_display()
                    v_u_17()
                end)
            end):set_auto_zoffset_behaviour(true))
            v_u_1:button_add_enabled_anim(v_u_20, function() --[[ Line: 46 ]]
                --[[ Upvalues: (ref 1): p_u_7 ]]
                return p_u_7:get_alpha();
            end)
            v_u_10:refresh_display()
        end;
        v_u_10.refresh_display = function(p22) --[[ Name: refresh_display ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_2, (copy 3): p_u_6, (copy 4): p_u_9, (ref 5): v_u_5 ]]
            local v23 = v_u_14()
            if v_u_2:singleton():contains_key(v23) then
                p22:set_visible(true)
                if p_u_6._player_blob_manager:is_songkey_favorite(v23) == true then
                    p_u_9.Image = v_u_5:get_unfavorite_icon()
                    return p22;
                else
                    p_u_9.Image = v_u_5:get_favorite_icon()
                    return p22;
                end;
            else
                p22:set_visible(false)
                return p22;
            end;
        end;
        v_u_10.set_visible = function(p24, p25) --[[ Name: set_visible ]] --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_14, (ref 3): v_u_2 ]]
            v_u_20:set_visible(p25)
            if p25 then
                if v_u_2:singleton():get_songkey_priority((v_u_14())) == v_u_2.SongPriority.Hidden then
                    v_u_20:set_enabled(false)
                    return p24;
                end;
                v_u_20:set_enabled(true)
            end;
            return p24;
        end;
        f_cons()
        return v_u_10;
    end
};
