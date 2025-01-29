<?xml version="1.0" encoding="utf-8" ?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <xsl:template match="/*">
    <html>
      <head>
        <title>X4 NPC State Machines</title>
        <!-- HACK - reusing CSS for scriptproperties, loading from different folder, may not work in all browsers -->
        <link rel="stylesheet" type="text/css" href="../libraries/scriptproperties.css"/>
      </head>
      <body>
        <h1>NPC State Machine Structure:</h1>
        <!-- Process all sub-cues of Base -->
        <xsl:apply-templates select="cues/cue[@name='Base']/cues/cue" mode="state" />
      </body>
    </html>
  </xsl:template>

  <xsl:template match="cue" mode="state">
    <!-- Check if this cue is a STATE cue and display it -->
    <xsl:choose>
      <xsl:when test="starts-with(@name,'STATE_')">
        <p style="margin-left: 40px">
          <xsl:value-of select="@name" />
          <!-- Look for transitions from this state -->
          <span style="font-size:small; color:grey">
            transitions to:
            <xsl:apply-templates select="." mode="transitions" />
          </span>
          <!-- Look for STATE sub-cues -->
          <xsl:apply-templates select="cues/cue" mode="state" />
        </p>
      </xsl:when>
      <xsl:otherwise>
        <!-- look for STATE sub-cues (shouldn't exist, but just in case) -->
        <xsl:apply-templates select="cues/cue" mode="state" />
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="cue" mode="transitions">
    <!-- Search for a transition action in this cue and all non-state sub-cues -->
    <xsl:apply-templates select="actions//signal_cue_instantly" />
    <xsl:apply-templates select="cues/cue[not(starts-with(@name,'STATE_'))]" mode="transitions" />
  </xsl:template>

  <xsl:template match="signal_cue_instantly[@cue='ChangeState' and starts-with(@param,'STATE_')]">
    <xsl:value-of select="substring(@param,7)" />,
  </xsl:template>
</xsl:stylesheet>
