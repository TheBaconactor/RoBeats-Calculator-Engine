-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:04 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = {
    ["Adapter"] = {}
}
local v_u_5 = {
    ["Hidden"] = 0,
    ["FadeIn"] = 1,
    ["TextScrollIn"] = 2,
    ["Displayed"] = 3,
    ["FadeOut"] = 4
}
v4.Adapter.new = function(_) --[[ Name: new ]] --[[ Line: 23 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    local v6 = v_u_3:SPUIObjectBase()
    v6.layout = function(_) end;
    v6.set_scale = function(_, _) end;
    return v6;
end;
v4.new = function(_, p_u_7, p_u_8, p_u_9, p_u_10) --[[ Name: new ]] --[[ Line: 30 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_1, (copy 3): v_u_2 ]]
    local v_u_11 = {}
    local l_Hidden_0 = v_u_5.Hidden
    local v_u_12 = 0
    local v_u_13 = nil
    local v_u_14 = nil
    local v_u_15 = nil
    local v_u_16 = nil
    local v_u_17 = ""
    local v_u_18 = 0
    local function f_cons() --[[ Name: cons ]] --[[ Line: 44 ]]
        --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_8, (ref 3): v_u_14, (ref 4): v_u_15, (ref 5): v_u_1, (ref 6): v_u_16, (copy 7): p_u_7, (copy 8): p_u_10, (copy 9): v_u_11 ]]
        pcall(function() --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): p_u_8 ]]
            v_u_13 = p_u_8.SurfaceGui.Frame.NameDisplay
        end)
        pcall(function() --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): p_u_8 ]]
            v_u_14 = p_u_8.SurfaceGui.Frame.TextDisplay
        end)
        v_u_15 = v_u_1:get_list_of_children_of_classname(p_u_8, "TextLabel")
        v_u_16 = v_u_1:get_list_of_children_of_classname(p_u_8, "ImageLabel")
        if v_u_13 ~= nil then
            v_u_13.Text = p_u_7
        end;
        v_u_14.Text = ""
        if p_u_10 ~= nil and typeof(p_u_10.OnCreate) == "function" then
            p_u_10.OnCreate(v_u_11)
        end;
        v_u_11:set_alpha(0)
    end;
    v_u_11.update = function(p19, p20) --[[ Name: update ]] --[[ Line: 67 ]]
        --[[ Upvalues: (ref 1): l_Hidden_0, (ref 2): v_u_5, (ref 3): v_u_18, (ref 4): v_u_12, (ref 5): v_u_2, (copy 6): p_u_9, (ref 7): v_u_17, (ref 8): v_u_14 ]]
        if l_Hidden_0 ~= v_u_5.Displayed then
            v_u_18 = 0
        end;
        if l_Hidden_0 ~= v_u_5.Hidden then
            if l_Hidden_0 == v_u_5.FadeIn then
                local v21, v22 = v_u_2:incr_clamp(v_u_12, v_u_2:SecondsToTick(0.25) * p20, 0, 1)
                v_u_12 = v21
                p_u_9:set_scale(v_u_2:YForPointOf2PtLine(Vector2.new(0, 1.2), Vector2.new(1, 1), v_u_2:BezierYForT(0, 0, 0.2, -0.2, 0.8, 1.2, 1, 1, v_u_12)))
                p19:set_alpha(v_u_2:YForPointOf2PtLine(Vector2.new(0, 0), Vector2.new(1, 0.9), v_u_12))
                if v22 == true then
                    l_Hidden_0 = v_u_5.TextScrollIn
                    v_u_12 = 0
                    return;
                end;
            elseif l_Hidden_0 == v_u_5.TextScrollIn then
                p19:set_alpha(1)
                v_u_12 = v_u_12 + v_u_2:SecondsToTick(0.025) * p20
                local v23 = #v_u_17
                v_u_14.Text = string.sub(v_u_17, 1, (math.floor(v_u_12)))
                if v23 <= v_u_12 then
                    l_Hidden_0 = v_u_5.Displayed
                    v_u_12 = 0
                    return;
                end;
            else
                if l_Hidden_0 == v_u_5.Displayed then
                    v_u_18 = v_u_18 + v_u_2:TimescaleToDeltaTime(p20)
                    p19:set_alpha(1)
                    return;
                end;
                if l_Hidden_0 == v_u_5.FadeOut then
                    local v24, v25 = v_u_2:incr_clamp(v_u_12, v_u_2:SecondsToTick(0.25) * p20, 0, 1)
                    v_u_12 = v24
                    p_u_9:set_scale(v_u_2:YForPointOf2PtLine(Vector2.new(0, 1), Vector2.new(1, 0.8), v_u_2:BezierYForT(0, 0, 0.2, -0.2, 0.8, 1.2, 1, 1, v_u_12)))
                    p19:set_alpha(v_u_2:YForPointOf2PtLine(Vector2.new(0, 0.9), Vector2.new(1, 0), v_u_12))
                    if v25 == true then
                        l_Hidden_0 = v_u_5.Hidden
                        v_u_12 = 0
                    end;
                end;
            end;
        end;
    end;
    v_u_11.display_text = function(_, p26) --[[ Name: display_text ]] --[[ Line: 143 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_14, (ref 3): l_Hidden_0, (ref 4): v_u_5, (ref 5): v_u_12 ]]
        v_u_17 = p26
        v_u_14.Text = ""
        if l_Hidden_0 == v_u_5.Hidden then
            l_Hidden_0 = v_u_5.FadeIn
            v_u_12 = 0
            return;
        elseif l_Hidden_0 == v_u_5.FadeIn then
            l_Hidden_0 = v_u_5.FadeIn
            return;
        elseif l_Hidden_0 == v_u_5.TextScrollIn then
            l_Hidden_0 = v_u_5.TextScrollIn
            v_u_12 = 0
            return;
        elseif l_Hidden_0 == v_u_5.Displayed then
            l_Hidden_0 = v_u_5.TextScrollIn
            v_u_12 = 0
        elseif l_Hidden_0 == v_u_5.FadeOut then
            l_Hidden_0 = v_u_5.FadeIn
            v_u_12 = 0
        end;
    end;
    v_u_11.is_displayed = function(_) --[[ Name: is_displayed ]] --[[ Line: 163 ]]
        --[[ Upvalues: (ref 1): l_Hidden_0, (ref 2): v_u_5 ]]
        return l_Hidden_0 == v_u_5.Displayed;
    end;
    v_u_11.get_time_displayed = function(_) --[[ Name: get_time_displayed ]] --[[ Line: 164 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        return v_u_18;
    end;
    v_u_11.is_fading_out = function(_) --[[ Name: is_fading_out ]] --[[ Line: 166 ]]
        --[[ Upvalues: (ref 1): l_Hidden_0, (ref 2): v_u_5 ]]
        return l_Hidden_0 == v_u_5.FadeOut and true or l_Hidden_0 == v_u_5.Hidden;
    end;
    v_u_11.is_hidden = function(_) --[[ Name: is_hidden ]] --[[ Line: 167 ]]
        --[[ Upvalues: (ref 1): l_Hidden_0, (ref 2): v_u_5 ]]
        return l_Hidden_0 == v_u_5.Hidden;
    end;
    v_u_11.force_hide = function(_) --[[ Name: force_hide ]] --[[ Line: 168 ]]
        --[[ Upvalues: (ref 1): l_Hidden_0, (ref 2): v_u_5 ]]
        l_Hidden_0 = v_u_5.Hidden
    end;
    v_u_11.force_display = function(_) --[[ Name: force_display ]] --[[ Line: 170 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_17, (ref 3): l_Hidden_0, (ref 4): v_u_5 ]]
        v_u_14.Text = v_u_17
        l_Hidden_0 = v_u_5.Displayed
    end;
    v_u_11.finish = function(_) --[[ Name: finish ]] --[[ Line: 175 ]]
        --[[ Upvalues: (ref 1): l_Hidden_0, (ref 2): v_u_5, (ref 3): v_u_12 ]]
        if l_Hidden_0 == v_u_5.Hidden then
            return;
        elseif l_Hidden_0 == v_u_5.FadeIn then
            l_Hidden_0 = v_u_5.FadeOut
            v_u_12 = 0
            return;
        elseif l_Hidden_0 == v_u_5.TextScrollIn then
            l_Hidden_0 = v_u_5.FadeOut
            v_u_12 = 0
            return;
        elseif l_Hidden_0 == v_u_5.Displayed then
            l_Hidden_0 = v_u_5.FadeOut
            v_u_12 = 0
        end;
    end;
    v_u_11.layout = function(_) --[[ Name: layout ]] --[[ Line: 190 ]]
        --[[ Upvalues: (copy 1): p_u_9 ]]
        p_u_9:layout()
    end;
    local v_u_27 = false
    v_u_11.use_r_set_alpha_v2 = function(p28) --[[ Name: use_r_set_alpha_v2 ]] --[[ Line: 200 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        v_u_27 = true
        return p28;
    end;
    local v_u_29 = -1
    v_u_11.set_alpha = function(_, p30) --[[ Name: set_alpha ]] --[[ Line: 206 ]]
        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_27, (ref 3): v_u_1, (ref 4): v_u_15, (ref 5): v_u_16, (copy 6): p_u_8 ]]
        if v_u_29 ~= p30 then
            v_u_29 = p30
            if v_u_27 then
                v_u_1:list_apply_suffix_alpha_attribute(v_u_15, "CharacterDialogue", v_u_29)
                v_u_1:list_apply_suffix_alpha_attribute(v_u_16, "CharacterDialogue", v_u_29)
                v_u_1:r_set_alpha_v2(p_u_8, v_u_29)
                return;
            end;
            v_u_1:list_set_alpha_name(v_u_15, {
                ["TextAlpha"] = v_u_29
            })
            v_u_1:list_set_alpha_name(v_u_16, {
                ["ImageAlpha"] = v_u_29
            })
            v_u_1:r_set_alpha(p_u_8, v_u_29, nil)
        end;
    end;
    f_cons()
    return v_u_11;
end;
return v4;
