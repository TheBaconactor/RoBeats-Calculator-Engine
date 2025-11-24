-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:01 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
return {
    ["new"] = function(_, p_u_7, p8, p9, p_u_10) --[[ Name: new ]] --[[ Line: 10 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_3, (copy 5): v_u_4, (copy 6): v_u_6 ]]
        local v_u_11 = nil
        v_u_11 = v_u_1:new(v_u_2:new(p8, p9, p_u_10), p_u_7._spui, function() --[[ Line: 15 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11:play_pressed()
        end)
        local v_u_12 = -1
        local v_u_13 = v_u_5:get_list_of_children_of_classname(p_u_10, "ImageLabel")
        local v_u_14 = v_u_5:get_list_of_children_of_classname(p_u_10, "TextLabel")
        local v_u_15 = false
        local v_u_16 = nil
        v_u_11:set_enabled_anim_updatefn(function(_, p17) --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16 ]]
            v_u_15 = true
            v_u_16 = p17
        end)
        local v_u_18 = nil
        v_u_11.play_pressed = function(p19) --[[ Name: play_pressed ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_3, (copy 3): p_u_7, (ref 4): v_u_4 ]]
            if v_u_18 == nil then
                v_u_3:puts("SongPreviewUIButton:play_pressed target_songkey is nil")
                return;
            elseif p_u_7._bgm_manager:is_preview_song_loading() == true then
                v_u_3:puts("SongPreviewUIButton:play_pressed is_loading")
                return;
            elseif p_u_7._bgm_manager:get_preview_songkey() == v_u_18 then
                v_u_3:puts("SongPreviewUIButton:play_pressed is_previewing same")
                return;
            elseif p19:get_visible() == true then
                p_u_7._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
                p_u_7._bgm_manager:preview_songkey(v_u_18)
                p19:set_enabled(false)
            end;
        end;
        v_u_11.set_target_songkey = function(p20, p21) --[[ Name: set_target_songkey ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18 = p21
            if p20:get_visible() == true then
                if v_u_18 == nil then
                    p20:set_enabled(false)
                end;
            end;
        end;
        local v_u_22 = ""
        local function f_set_text(p23) --[[ Name: set_text ]] --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): v_u_22, (copy 2): v_u_14 ]]
            if p23 ~= v_u_22 then
                v_u_22 = p23
                for v24 = 1, v_u_14:count() do
                    v_u_14:get(v24).Text = v_u_22
                end;
            end;
        end;
        v_u_11.behaviour_update = function(p25, _, _) --[[ Name: behaviour_update ]] --[[ Line: 75 ]]
            --[[ Upvalues: (copy 1): p_u_7, (ref 2): v_u_18, (copy 3): f_set_text, (ref 4): v_u_15, (ref 5): v_u_6, (ref 6): v_u_16, (ref 7): v_u_12, (ref 8): v_u_5, (copy 9): v_u_13, (copy 10): v_u_14, (copy 11): p_u_10 ]]
            local v26 = p_u_7._bgm_manager:get_preview_songkey()
            local v27 = p_u_7._bgm_manager:is_preview_song_loading() or p_u_7._bgm_manager:is_preview_transitioning()
            local v28 = v26 == v_u_18
            if p25:get_visible() == true then
                if v_u_18 == nil then
                    p25:set_enabled(false)
                    f_set_text("")
                elseif v27 then
                    p25:set_enabled(false)
                    f_set_text("Loading...")
                elseif v28 then
                    p25:set_enabled(false)
                    f_set_text("Playing")
                else
                    p25:set_enabled(true)
                    f_set_text("Preview")
                end;
            end;
            if v_u_15 == true then
                v_u_15 = false
                local v29 = v_u_6:YForPointOf2PtLine(Vector2.new(0, 0.5), Vector2.new(1, 1), v_u_16)
                if v_u_12 ~= v29 then
                    v_u_12 = v29
                    v_u_5:list_set_alpha_name(v_u_13, {
                        ["ImageAlpha"] = v_u_12
                    })
                    v_u_5:list_set_alpha_name(v_u_14, {
                        ["TextAlpha"] = v_u_12
                    })
                    v_u_5:r_set_alpha(p_u_10, p25:get_alpha())
                end;
            end;
        end;
        return v_u_11;
    end
};
